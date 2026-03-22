"""
🎤 ClipVox - Kling AI Lip Sync Service (via PiAPI)
Fluxo:
  1. Converte áudio para MP3 (compatível + leve) via ffmpeg
  2. Trima o áudio para a duração exata do vídeo (ffprobe + ffmpeg)
  3. Faz upload dos vocals/áudio para Cloudflare R2
  4. Verifica acessibilidade pública das URLs antes de enviar ao Kling
  5. Envia para PiAPI (Kling lip sync)
  6. Faz polling até concluir
  7. Salva resultado no R2 e retorna a URL

Ajustes desta versão:
  - sessões HTTP sem herdar proxies do ambiente
  - timeouts maiores e separados (connect/read)
  - erro estruturado para busy / no_face / too_large / proxy / timeout / deleted
  - origin_task_id mantido em TODAS as tentativas quando disponível
  - fallback de compressão sem voltar para o vídeo original quando ele excede o limite
"""

import os
import time
import json
import subprocess
from typing import Optional, Dict, Any, Tuple

import boto3
import requests

PIAPI_API_KEY = os.getenv("PIAPI_API_KEY", "")
PIAPI_BASE = "https://api.piapi.ai"
IMGBB_KEY = os.getenv("IMGBB_API_KEY", "")
R2_ACCESS_KEY = os.getenv("R2_ACCESS_KEY_ID", "")
R2_SECRET_KEY = os.getenv("R2_SECRET_ACCESS_KEY", "")
R2_ENDPOINT = os.getenv("R2_ENDPOINT_URL", "")
R2_BUCKET_NAME = os.getenv("R2_BUCKET_NAME", "clipvox-images")
R2_PUBLIC_URL = os.getenv("R2_PUBLIC_URL", "").rstrip("/")

CONNECT_TIMEOUT = 10
READ_TIMEOUT_API = 180
READ_TIMEOUT_POLL = 60
READ_TIMEOUT_DOWNLOAD = 180
READ_TIMEOUT_UPLOAD_CHECK = 30
POLL_INTERVAL_SECONDS = 15
DEFAULT_LIPSYNC_TIMEOUT = 600
MAX_REMOTE_VIDEO_MB = 9
SAFE_COMPRESSED_VIDEO_MB = 7

_HTTP_SESSION: Optional[requests.Session] = None


# ═══════════════════════════════════════════════════════════════
# HTTP / AUTH
# ═══════════════════════════════════════════════════════════════
def _http_session() -> requests.Session:
    global _HTTP_SESSION
    if _HTTP_SESSION is None:
        s = requests.Session()
        s.trust_env = False  # não herda HTTP_PROXY/HTTPS_PROXY do ambiente
        s.headers.update({"User-Agent": "ClipVox/1.0"})
        _HTTP_SESSION = s
    return _HTTP_SESSION


def _auth_headers() -> dict:
    if not PIAPI_API_KEY:
        raise ValueError("PIAPI_API_KEY não configurada")
    return {
        "Content-Type": "application/json",
        "x-api-key": PIAPI_API_KEY,
    }


def _ok(**kwargs) -> Dict[str, Any]:
    payload = {"success": True}
    payload.update(kwargs)
    return payload


def _fail(error: str, error_type: str = "unknown", **kwargs) -> Dict[str, Any]:
    payload = {
        "success": False,
        "error": error,
        "error_type": error_type,
    }
    payload.update(kwargs)
    return payload


def _classify_error(raw_message: str) -> str:
    text = (raw_message or "").lower()
    if not text:
        return "unknown"
    if "service busy" in text or "submit task failed: 500" in text:
        return "busy"
    if "proxyconnect" in text or "connection refused" in text or "proxy" in text:
        return "proxy"
    if "read timed out" in text or "timed out" in text:
        return "timeout"
    if "identify failed" in text or "status 609" in text or "no face" in text:
        return "no_face"
    if "too large" in text or "maximum is 10mb" in text or "file size" in text:
        return "too_large"
    if "404 not found" in text or "deleted the task" in text:
        return "deleted"
    if "não acessível" in text or "not accessible" in text:
        return "inaccessible"
    if "cancelled" in text:
        return "cancelled"
    return "unknown"


def _format_error_message(error_type: str, raw_message: str) -> str:
    msg = (raw_message or "Falha desconhecida").strip()
    return f"[{error_type}] {msg}"


def _extract_piapi_raw_message(data: Dict[str, Any]) -> str:
    return (
        data.get("data", {}).get("error", {}).get("raw_message", "")
        or data.get("data", {}).get("error", {}).get("message", "")
        or data.get("message", "")
        or "sem mensagem"
    )


def _print_long_error(prefix: str, raw_msg: str) -> None:
    print(prefix)
    raw_msg = raw_msg or "sem mensagem"
    for i in range(0, len(raw_msg), 200):
        print(f"      {raw_msg[i:i+200]}")


# ═══════════════════════════════════════════════════════════════
# FFPROBE / FFMPEG HELPERS
# ═══════════════════════════════════════════════════════════════
def _get_video_duration(video_url: str) -> Optional[float]:
    try:
        result = subprocess.run(
            [
                "ffprobe", "-v", "quiet",
                "-print_format", "json",
                "-show_format",
                video_url,
            ],
            capture_output=True,
            text=True,
            timeout=30,
        )
        if result.returncode == 0:
            info = json.loads(result.stdout or "{}")
            duration = float(info.get("format", {}).get("duration", 0) or 0)
            if duration > 0:
                print(f"   ⏱️ Duração do vídeo detectada: {duration:.2f}s")
                return duration
        print("   ⚠️ ffprobe não retornou duração válida")
        return None
    except Exception as e:
        print(f"   ⚠️ ffprobe erro: {e}")
        return None


def _get_audio_duration(audio_path: str) -> Optional[float]:
    try:
        result = subprocess.run(
            [
                "ffprobe", "-v", "quiet",
                "-print_format", "json",
                "-show_format",
                audio_path,
            ],
            capture_output=True,
            text=True,
            timeout=15,
        )
        if result.returncode == 0:
            info = json.loads(result.stdout or "{}")
            duration = float(info.get("format", {}).get("duration", 0) or 0)
            return duration if duration > 0 else None
        return None
    except Exception:
        return None


def _convert_to_mp3(audio_path: str, job_id: str = "") -> str:
    ext = audio_path.rsplit(".", 1)[-1].lower()
    if ext == "mp3":
        return audio_path

    from config import UPLOAD_DIR

    mp3_filename = f"{job_id}_lipsync_audio.mp3" if job_id else f"lipsync_{int(time.time())}.mp3"
    mp3_path = os.path.join(UPLOAD_DIR, mp3_filename)

    print(f"   🔄 Convertendo {ext.upper()} → MP3 para compatibilidade com Kling...")
    try:
        result = subprocess.run(
            [
                "ffmpeg", "-y", "-i", audio_path,
                "-vn", "-ar", "44100", "-ac", "2", "-b:a", "128k",
                mp3_path,
            ],
            capture_output=True,
            text=True,
            timeout=120,
        )
        if result.returncode == 0 and os.path.exists(mp3_path):
            original_size = os.path.getsize(audio_path) // 1024
            mp3_size = os.path.getsize(mp3_path) // 1024
            print(f"   ✅ Convertido: {original_size}KB → {mp3_size}KB MP3")
            return mp3_path
        print(f"   ⚠️ ffmpeg falhou ({result.stderr[-200:] if result.stderr else 'sem stderr'}), usando original")
        return audio_path
    except Exception as e:
        print(f"   ⚠️ Erro conversão MP3: {e}, usando original")
        return audio_path


def _trim_audio(audio_path: str, duration: float, job_id: str = "") -> str:
    try:
        audio_duration = _get_audio_duration(audio_path)
        if audio_duration and audio_duration <= duration + 0.5:
            print(f"   ✅ Áudio ({audio_duration:.1f}s) ≤ vídeo ({duration:.1f}s) — sem trim necessário")
            return audio_path

        from config import UPLOAD_DIR

        ext = audio_path.rsplit(".", 1)[-1].lower()
        trimmed_path = os.path.join(UPLOAD_DIR, f"{job_id}_trimmed.{ext}")

        original = f"{audio_duration:.1f}s" if audio_duration else "desconhecida"
        print(f"   ✂️ Trimando áudio: {original} → {duration:.1f}s (duração do clipe)")

        input_ext = audio_path.rsplit(".", 1)[-1].lower()
        output_ext = trimmed_path.rsplit(".", 1)[-1].lower()
        if input_ext != output_ext or input_ext == "wav":
            codec_args = ["-acodec", "libmp3lame", "-ab", "128k"]
        else:
            codec_args = ["-c", "copy"]

        result = subprocess.run(
            ["ffmpeg", "-y", "-i", audio_path, "-t", str(duration)] + codec_args + [trimmed_path],
            capture_output=True,
            text=True,
            timeout=60,
        )
        if result.returncode == 0 and os.path.exists(trimmed_path):
            trimmed_size = os.path.getsize(trimmed_path) // 1024
            print(f"   ✅ Áudio trimado: {trimmed_size}KB ({duration:.1f}s)")
            return trimmed_path
        print(f"   ⚠️ Trim falhou: {result.stderr[-200:] if result.stderr else 'sem stderr'}")
        return audio_path
    except Exception as e:
        print(f"   ⚠️ Erro ao trimar áudio: {e}")
        return audio_path


# ═══════════════════════════════════════════════════════════════
# R2 / IMGBB HELPERS
# ═══════════════════════════════════════════════════════════════
def _upload_face_imgbb(face_path: str) -> Optional[str]:
    import base64

    try:
        with open(face_path, "rb") as f:
            b64 = base64.b64encode(f.read()).decode()
        resp = _http_session().post(
            f"https://api.imgbb.com/1/upload?key={IMGBB_KEY}",
            data={"image": b64, "name": f"clipvox_face_{int(time.time())}"},
            timeout=(CONNECT_TIMEOUT, 60),
        )
        if resp.status_code == 200:
            url = resp.json().get("data", {}).get("url")
            if url:
                time.sleep(2)
                print(f"   ✅ imgbb face: {url}")
                return url
        print(f"   ❌ imgbb falhou: HTTP {resp.status_code}")
        return None
    except Exception as e:
        print(f"   ❌ imgbb erro: {e}")
        return None


def get_r2_client():
    print("✅ CloudFlare R2 client initialized")
    return boto3.client(
        "s3",
        endpoint_url=R2_ENDPOINT,
        aws_access_key_id=R2_ACCESS_KEY,
        aws_secret_access_key=R2_SECRET_KEY,
        region_name="auto",
    )


def _upload_file_to_r2(local_path: str, r2_key: str, content_type: str) -> Optional[str]:
    try:
        r2_client = get_r2_client()
        with open(local_path, "rb") as f:
            r2_client.put_object(
                Bucket=R2_BUCKET_NAME,
                Key=r2_key,
                Body=f,
                ContentType=content_type,
            )
        public_url = f"{R2_PUBLIC_URL}/{r2_key}"
        return public_url
    except Exception as e:
        print(f"   ❌ Erro upload R2 ({r2_key}): {e}")
        return None


def _upload_audio_to_r2(audio_path: str, job_id: str = "") -> Optional[str]:
    filename = os.path.basename(audio_path)
    ext = filename.rsplit(".", 1)[-1].lower()
    ct_map = {
        "mp3": "audio/mpeg",
        "wav": "audio/wav",
        "ogg": "audio/ogg",
        "m4a": "audio/mp4",
        "aac": "audio/aac",
        "flac": "audio/flac",
    }
    content_type = ct_map.get(ext, "audio/mpeg")
    r2_key = f"audio/{job_id}/{filename}"
    print(f"   📤 Upload áudio → R2: {filename}")
    public_url = _upload_file_to_r2(audio_path, r2_key, content_type)
    if public_url:
        print(f"   ✅ Áudio no R2: {public_url}")
    return public_url


def _upload_video_file_to_r2(video_path: str, job_id: str, filename: str) -> Optional[str]:
    r2_key = f"clips/{job_id}/{filename}"
    public_url = _upload_file_to_r2(video_path, r2_key, "video/mp4")
    if public_url:
        print(f"   ✅ Vídeo no R2: {public_url}")
    return public_url


def _upload_lipsync_to_r2(video_url: str, job_id: str) -> Optional[str]:
    try:
        from config import UPLOAD_DIR

        resp = _http_session().get(video_url, timeout=(CONNECT_TIMEOUT, READ_TIMEOUT_DOWNLOAD), stream=True)
        if resp.status_code != 200:
            return None
        local_path = os.path.join(UPLOAD_DIR, f"{job_id}_lipsync.mp4")
        with open(local_path, "wb") as f:
            for chunk in resp.iter_content(8192):
                if chunk:
                    f.write(chunk)
        r2_key = f"lipsync/{job_id}/lipsync.mp4"
        r2_url = _upload_file_to_r2(local_path, r2_key, "video/mp4")
        if r2_url:
            print(f"   ✅ Lip sync no R2: {r2_url}")
        return r2_url
    except Exception as e:
        print(f"   ⚠️ Erro salvar lip sync R2: {e}")
        return None


# ═══════════════════════════════════════════════════════════════
# URL / SIZE HELPERS
# ═══════════════════════════════════════════════════════════════
def _head_or_get_headers(url: str) -> Tuple[int, Dict[str, str]]:
    session = _http_session()
    try:
        resp = session.head(url, timeout=(CONNECT_TIMEOUT, READ_TIMEOUT_UPLOAD_CHECK), allow_redirects=True)
        if resp.status_code < 400:
            return resp.status_code, dict(resp.headers)
    except Exception:
        pass
    try:
        resp = session.get(url, timeout=(CONNECT_TIMEOUT, READ_TIMEOUT_UPLOAD_CHECK), allow_redirects=True, stream=True)
        try:
            return resp.status_code, dict(resp.headers)
        finally:
            resp.close()
    except Exception:
        return 0, {}


def _check_url_accessible(url: str, label: str) -> bool:
    try:
        status, headers = _head_or_get_headers(url)
        if status == 200:
            size = headers.get("Content-Length")
            size_text = f", {int(size) // 1024}KB" if size and size.isdigit() else ""
            print(f"   ✅ {label} acessível (HTTP 200{size_text})")
            return True
        print(f"   ❌ {label} NÃO acessível (HTTP {status}) — Kling vai falhar!")
        print(f"      URL: {url}")
        return False
    except Exception as e:
        print(f"   ⚠️ {label} — erro ao verificar: {e}")
        return False


def _estimate_remote_size_mb(video_url: str) -> Optional[float]:
    status, headers = _head_or_get_headers(video_url)
    if status != 200:
        return None
    content_length = headers.get("Content-Length") or headers.get("content-length")
    if content_length and str(content_length).isdigit():
        return int(content_length) / (1024 * 1024)
    return None


def _download_and_compress_video(video_url: str, job_id: str, max_mb: int = SAFE_COMPRESSED_VIDEO_MB) -> Optional[str]:
    from config import UPLOAD_DIR

    session = _http_session()
    raw_path = os.path.join(UPLOAD_DIR, f"{job_id}_raw_clip.mp4")
    compressed_path = os.path.join(UPLOAD_DIR, f"{job_id}_compressed_clip.mp4")
    compressed_path_2 = os.path.join(UPLOAD_DIR, f"{job_id}_compressed_clip_fallback.mp4")

    try:
        print("   📥 Baixando vídeo para verificar/comprimir...")
        resp = session.get(video_url, timeout=(CONNECT_TIMEOUT, READ_TIMEOUT_DOWNLOAD), stream=True)
        if resp.status_code != 200:
            print(f"   ❌ Download vídeo falhou: HTTP {resp.status_code}")
            return None
        with open(raw_path, "wb") as f:
            for chunk in resp.iter_content(8192):
                if chunk:
                    f.write(chunk)

        size_mb = os.path.getsize(raw_path) / (1024 * 1024)
        print(f"   📦 Tamanho do vídeo: {size_mb:.2f}MB (alvo: ≤ {max_mb}MB)")
        if size_mb <= max_mb:
            print("   ✅ Vídeo dentro do limite — sem compressão necessária")
            return raw_path

        duration = _get_video_duration(raw_path) or 5.0
        target_kbps = max(400, int((max_mb * 8 * 1024) / duration * 0.78))
        print(f"   🗜️ Compressão 1: bitrate alvo {target_kbps}kbps")
        result = subprocess.run(
            [
                "ffmpeg", "-y", "-i", raw_path,
                "-vf", "scale='min(1280,iw)':-2,fps=24",
                "-c:v", "libx264", "-preset", "veryfast", "-b:v", f"{target_kbps}k",
                "-maxrate", f"{int(target_kbps * 1.1)}k", "-bufsize", f"{target_kbps * 2}k",
                "-c:a", "aac", "-b:a", "96k",
                "-movflags", "+faststart",
                compressed_path,
            ],
            capture_output=True,
            text=True,
            timeout=180,
        )
        if result.returncode == 0 and os.path.exists(compressed_path):
            new_mb = os.path.getsize(compressed_path) / (1024 * 1024)
            print(f"   ✅ Compressão 1: {size_mb:.2f}MB → {new_mb:.2f}MB")
            if new_mb <= max_mb:
                return compressed_path

        print("   🗜️ Compressão 2 (fallback): reduzindo resolução/qualidade...")
        result = subprocess.run(
            [
                "ffmpeg", "-y", "-i", raw_path,
                "-vf", "scale='min(960,iw)':-2,fps=24",
                "-c:v", "libx264", "-preset", "veryfast", "-crf", "32",
                "-c:a", "aac", "-b:a", "64k",
                "-movflags", "+faststart",
                compressed_path_2,
            ],
            capture_output=True,
            text=True,
            timeout=180,
        )
        if result.returncode == 0 and os.path.exists(compressed_path_2):
            new_mb = os.path.getsize(compressed_path_2) / (1024 * 1024)
            print(f"   ✅ Compressão 2: {size_mb:.2f}MB → {new_mb:.2f}MB")
            if new_mb <= max_mb:
                return compressed_path_2

        print("   ⚠️ Não foi possível comprimir abaixo do limite com segurança")
        return compressed_path_2 if os.path.exists(compressed_path_2) else None
    except Exception as e:
        print(f"   ❌ Erro ao baixar/comprimir vídeo: {e}")
        return None


# ═══════════════════════════════════════════════════════════════
# PIAPI LIP SYNC
# ═══════════════════════════════════════════════════════════════
def create_lipsync_task(video_url: str, audio_url: str, model: str = "kling", origin_task_id: str = "") -> Dict[str, Any]:
    print("🎤 Criando task de Lip Sync via PiAPI...")
    if video_url:
        print(f"   Vídeo      : {video_url[:80]}")
    print(f"   Áudio      : {audio_url[:80]}")

    if origin_task_id:
        print(f"   🎯 Usando origin_task_id: {origin_task_id}")
        lipsync_input = {
            "origin_task_id": origin_task_id,
            "local_dubbing_url": audio_url,
            "tts_text": "",
            "tts_timbre": "",
            "tts_speed": 1,
        }
    else:
        lipsync_input = {
            "video_url": video_url,
            "local_dubbing_url": audio_url,
            "tts_text": "",
            "tts_timbre": "",
            "tts_speed": 1,
        }

    payload = {
        "model": model,
        "task_type": "lip_sync",
        "input": lipsync_input,
    }

    try:
        resp = _http_session().post(
            f"{PIAPI_BASE}/api/v1/task",
            headers=_auth_headers(),
            json=payload,
            timeout=(CONNECT_TIMEOUT, READ_TIMEOUT_API),
        )
        body_preview = resp.text[:300] if resp.text else ""
        print(f"   📥 HTTP {resp.status_code}: {body_preview}")
        data = resp.json()

        if data.get("code") != 200:
            raw_msg = _extract_piapi_raw_message(data)
            error_type = _classify_error(raw_msg)
            print(f"   ❌ Erro PiAPI code: {data.get('code')}")
            print(f"   ❌ message : {data.get('message')}")
            _print_long_error("   ❌ raw_message COMPLETO:", raw_msg)
            return _fail(_format_error_message(error_type, raw_msg), error_type, raw_error=raw_msg, http_status=resp.status_code)

        task_id = data.get("data", {}).get("task_id")
        if not task_id:
            return _fail("[unknown] PiAPI não retornou task_id", "unknown")
        print(f"   ✅ Task criada: {task_id}")
        return _ok(task_id=task_id)
    except requests.exceptions.ReadTimeout as e:
        msg = str(e)
        print(f"   ❌ Exceção PiAPI: {msg}")
        return _fail(_format_error_message("timeout", msg), "timeout", raw_error=msg)
    except requests.exceptions.ProxyError as e:
        msg = str(e)
        print(f"   ❌ Exceção PiAPI: {msg}")
        return _fail(_format_error_message("proxy", msg), "proxy", raw_error=msg)
    except Exception as e:
        msg = str(e)
        etype = _classify_error(msg)
        print(f"   ❌ Exceção PiAPI: {msg}")
        return _fail(_format_error_message(etype, msg), etype, raw_error=msg)


def poll_lipsync_task(task_id: str, timeout: int = DEFAULT_LIPSYNC_TIMEOUT) -> Dict[str, Any]:
    print(f"   ⏳ Aguardando lip sync (task {task_id})...")
    last_error_type = "unknown"
    last_error = ""

    for elapsed in range(POLL_INTERVAL_SECONDS, timeout + 1, POLL_INTERVAL_SECONDS):
        time.sleep(POLL_INTERVAL_SECONDS)
        try:
            resp = _http_session().get(
                f"{PIAPI_BASE}/api/v1/task/{task_id}",
                headers=_auth_headers(),
                timeout=(CONNECT_TIMEOUT, READ_TIMEOUT_POLL),
            )
            data = resp.json()
            task = data.get("data", {})
            status = task.get("status", "")
            print(f"   ⏳ Status: {status} ({elapsed}s)")

            if status == "completed":
                works = task.get("output", {}).get("works", []) or []
                if works:
                    url = works[0].get("video", {}).get("resource")
                    if url:
                        print(f"   ✅ Lip sync pronto: {url[:80]}")
                        return _ok(video_url=url, task_id=task_id)
                return _fail("[unknown] Nenhum vídeo no resultado do lip sync", "unknown")

            if status == "failed":
                error = task.get("error", {})
                raw_msg = error.get("raw_message", "") or error.get("message", "desconhecido")
                error_type = _classify_error(raw_msg)
                _print_long_error("   ❌ Lip sync falhou — raw_message COMPLETO:", raw_msg)
                return _fail(_format_error_message(error_type, raw_msg), error_type, raw_error=raw_msg)
        except requests.exceptions.ReadTimeout as e:
            last_error_type = "timeout"
            last_error = str(e)
            print(f"   ⚠️ Polling timeout: {last_error}")
        except Exception as e:
            last_error_type = _classify_error(str(e))
            last_error = str(e)
            print(f"   ⚠️ Polling erro: {last_error}")

    timeout_msg = last_error or f"Tempo máximo de {timeout}s atingido"
    return _fail(_format_error_message(last_error_type or 'timeout', timeout_msg), last_error_type or "timeout")


# ═══════════════════════════════════════════════════════════════
# FUNÇÃO PRINCIPAL
# ═══════════════════════════════════════════════════════════════
def generate_lipsync(
    face_source: str,
    audio_source: str,
    job_id: str = "",
    model: str = "kling",
    max_retries: int = 3,
    extract_vocals_first: bool = True,
    clip_duration: Optional[float] = None,
    preextracted_vocals: Optional[str] = None,
    origin_task_id: str = "",
) -> Dict[str, Any]:
    del extract_vocals_first  # mantido só por compatibilidade de assinatura

    # ── 1. Converter áudio para MP3 ───────────────────────────────────────────
    audio_path = _convert_to_mp3(audio_source, job_id)

    # ── 2. Usar vocals pré-extraídos quando disponíveis ───────────────────────
    if preextracted_vocals and os.path.isfile(preextracted_vocals):
        print(f"   🎵 Usando vocals pré-extraídos: {os.path.basename(preextracted_vocals)}")
        audio_path = _convert_to_mp3(preextracted_vocals, f"{job_id}_vocals")

    # ── 3. Trimar áudio para duração do clipe ─────────────────────────────────
    duration = clip_duration
    if not duration and not os.path.isfile(face_source):
        print("   🔍 Detectando duração do vídeo via ffprobe...")
        duration = _get_video_duration(face_source)

    if duration and duration > 0:
        audio_path = _trim_audio(audio_path, duration, job_id)
    else:
        print("   ⚠️ Duração do vídeo não detectada — enviando áudio sem trim")

    # ── 4. Resolver fonte do vídeo/rosto ──────────────────────────────────────
    face_url = face_source
    original_face_url = face_source
    compressed_mode = False
    compressed_local_path: Optional[str] = None

    if os.path.isfile(face_source):
        print("   📤 Hospedando imagem de rosto no imgbb...")
        face_url = _upload_face_imgbb(face_source)
        if not face_url:
            return _fail("[inaccessible] Falha ao hospedar imagem do rosto", "inaccessible")
        original_face_url = face_url
    elif origin_task_id:
        print("   🎯 origin_task_id disponível — mantendo esse modo em todas as tentativas")
    else:
        print(f"   🔍 Verificando tamanho do vídeo (limite Kling: {MAX_REMOTE_VIDEO_MB + 1}MB)...")
        estimated_mb = _estimate_remote_size_mb(face_source)
        if estimated_mb is not None:
            print(f"   📦 Tamanho estimado: {estimated_mb:.2f}MB")
        else:
            print("   ⚠️ Não foi possível estimar o tamanho remoto do vídeo")

        if estimated_mb and estimated_mb > MAX_REMOTE_VIDEO_MB:
            print(f"   🗜️ Vídeo > {MAX_REMOTE_VIDEO_MB}MB — comprimindo e hospedando no R2...")
            compressed_local_path = _download_and_compress_video(face_source, job_id, max_mb=SAFE_COMPRESSED_VIDEO_MB)
            if compressed_local_path:
                uploaded = _upload_video_file_to_r2(compressed_local_path, job_id, "compressed_clip.mp4")
                if uploaded:
                    face_url = uploaded
                    compressed_mode = True
                else:
                    return _fail("[inaccessible] Falha ao hospedar vídeo comprimido no R2", "inaccessible")
            else:
                return _fail("[too_large] Falha ao comprimir vídeo para lip sync", "too_large")
        else:
            print("   ✅ Vídeo dentro do limite — usando URL original")

    # ── 5. Upload do áudio para R2 ────────────────────────────────────────────
    print("   📤 Hospedando áudio no Cloudflare R2...")
    audio_url = _upload_audio_to_r2(audio_path, job_id)
    if not audio_url:
        return _fail("[inaccessible] Falha ao hospedar áudio no R2", "inaccessible")

    # ── 6. Verificar acessibilidade ───────────────────────────────────────────
    print("\n🔍 Verificando acessibilidade das URLs para o Kling...")
    audio_ok = _check_url_accessible(audio_url, "Áudio (R2)")
    if not audio_ok:
        return _fail(f"[inaccessible] URL do áudio R2 não acessível: {audio_url[:120]}", "inaccessible")

    if not origin_task_id:
        video_ok = _check_url_accessible(face_url, "Vídeo")
        if not video_ok:
            return _fail(f"[inaccessible] URL do vídeo não acessível: {face_url[:120]}", "inaccessible")

    # ── 7. Tentativas de lip sync ─────────────────────────────────────────────
    retryable_errors = {"busy", "proxy", "timeout", "deleted", "too_large"}
    last_result = _fail("[unknown] Lip sync não iniciado", "unknown")

    for attempt in range(1, max_retries + 1):
        print(f"\n🎤 Lip Sync — Tentativa {attempt}/{max_retries}")

        current_face_url = face_url
        current_origin_task_id = origin_task_id or ""

        if current_origin_task_id:
            print("   🎯 Mantendo origin_task_id nesta tentativa")
        elif compressed_mode:
            print("   🔒 Vídeo comprimido detectado — mantendo URL R2 em todas as tentativas")
        else:
            print("   🌐 Usando URL original do vídeo")

        create_result = create_lipsync_task(
            current_face_url,
            audio_url,
            model,
            origin_task_id=current_origin_task_id,
        )
        if not create_result["success"]:
            last_result = create_result
            # reação automática: se estourou tamanho sem compressão e ainda não comprimimos, tenta comprimir agora
            if (
                create_result.get("error_type") == "too_large"
                and not compressed_mode
                and not origin_task_id
                and not os.path.isfile(face_source)
            ):
                print("   🗜️ Erro de tamanho detectado em runtime — comprimindo vídeo para próxima tentativa...")
                compressed_local_path = _download_and_compress_video(face_source, job_id, max_mb=SAFE_COMPRESSED_VIDEO_MB)
                if compressed_local_path:
                    uploaded = _upload_video_file_to_r2(compressed_local_path, job_id, "compressed_clip_runtime.mp4")
                    if uploaded:
                        face_url = uploaded
                        compressed_mode = True
            if create_result.get("error_type") not in retryable_errors:
                break
            delay = 20 if attempt == 1 else 60 if attempt == 2 else 120
            print(f"   ⏳ Aguardando {delay}s antes de tentar novamente...")
            time.sleep(delay)
            continue

        task_id = create_result["task_id"]
        poll_result = poll_lipsync_task(task_id)
        if poll_result["success"]:
            final_video_url = poll_result["video_url"]
            r2_url = _upload_lipsync_to_r2(final_video_url, job_id)
            return _ok(video_url=r2_url or final_video_url, task_id=task_id)

        last_result = poll_result
        if poll_result.get("error_type") not in retryable_errors:
            break

        delay = 30 if attempt == 1 else 60 if attempt == 2 else 90
        print(f"   ⏳ Aguardando {delay}s antes de tentar novamente...")
        time.sleep(delay)

    print(f"   ❌ Lip sync falhou após {max_retries} tentativas — clipe será usado sem sincronização")
    if compressed_local_path and os.path.exists(compressed_local_path):
        try:
            os.remove(compressed_local_path)
        except Exception:
            pass
    return _fail(
        last_result.get("error") or f"[unknown] Lip sync falhou após {max_retries} tentativas",
        last_result.get("error_type", "unknown"),
    )
