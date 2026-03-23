"""
🎤 ClipVox - Kling AI Lip Sync Service (via PiAPI)
Corrigido para:
  - não herdar proxy do ambiente
  - manter origin_task_id em TODAS as tentativas
  - não voltar para URL original se o vídeo foi comprimido
  - timeouts maiores
  - classificar erro real (busy / no_face / too_large / deleted / timeout / proxy)
  - continuar compatível com o restante do backend
"""

import os
import time
import subprocess
from typing import Optional, Dict, Any

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


def _safe_session() -> requests.Session:
    session = requests.Session()
    session.trust_env = False
    return session


def _auth_headers() -> dict:
    if not PIAPI_API_KEY:
        raise ValueError("PIAPI_API_KEY não configurada")
    return {
        "Content-Type": "application/json",
        "x-api-key": PIAPI_API_KEY,
    }


def _classify_error(raw_text: str) -> str:
    text = (raw_text or "").lower()
    if "service busy" in text or "submit task failed: 500" in text or "server overloaded" in text:
        return "busy"
    if "identify failed" in text or "status 609" in text or "no face" in text or "face" in text and "detect" in text:
        return "no_face"
    if "404 not found" in text and ("deleted" in text or "content violation" in text or "kling deleted" in text):
        return "deleted"
    if "too large" in text or "maximum is 10mb" in text or "file size" in text:
        return "too_large"
    if "proxyconnect" in text or "connect: connection refused" in text or "proxy" in text:
        return "proxy"
    if "timed out" in text or "timeout" in text or "read timed out" in text:
        return "timeout"
    if "cancel" in text:
        return "cancelled"
    return "unknown"


def _error_result(message: str, raw_error: str = "", error_type: Optional[str] = None, **extra) -> Dict[str, Any]:
    result = {
        "success": False,
        "error": message,
        "raw_error": raw_error or message,
        "error_type": error_type or _classify_error(raw_error or message),
    }
    result.update(extra)
    return result


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
            import json
            info = json.loads(result.stdout)
            duration = float(info.get("format", {}).get("duration", 0))
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
            import json
            info = json.loads(result.stdout)
            return float(info.get("format", {}).get("duration", 0))
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
        print(f"   ⚠️ ffmpeg falhou ({result.stderr[-200:]}), usando original")
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

        trimmed_path = os.path.join(UPLOAD_DIR, f"{job_id}_trimmed.mp3")
        print(f"   ✂️ Trimando áudio: {audio_duration or 0:.1f}s → {duration:.1f}s (duração do clipe)")
        result = subprocess.run(
            [
                "ffmpeg", "-y", "-i", audio_path,
                "-t", str(duration),
                "-acodec", "libmp3lame", "-ab", "128k",
                trimmed_path,
            ],
            capture_output=True,
            text=True,
            timeout=60,
        )
        if result.returncode == 0 and os.path.exists(trimmed_path):
            trimmed_size = os.path.getsize(trimmed_path) // 1024
            print(f"   ✅ Áudio trimado: {trimmed_size}KB ({duration:.1f}s)")
            return trimmed_path
        print(f"   ⚠️ Trim falhou: {result.stderr[-200:]}")
        return audio_path
    except Exception as e:
        print(f"   ⚠️ Erro ao trimar áudio: {e}")
        return audio_path


def _download_and_compress_video(video_url: str, job_id: str, max_mb: int = 7) -> Optional[str]:
    from config import UPLOAD_DIR

    try:
        print("   📥 Baixando vídeo para verificar tamanho...")
        session = _safe_session()
        resp = session.get(video_url, timeout=(10, 120), stream=True)
        if resp.status_code != 200:
            print(f"   ❌ Download vídeo falhou: HTTP {resp.status_code}")
            return None

        raw_path = os.path.join(UPLOAD_DIR, f"{job_id}_raw_clip.mp4")
        with open(raw_path, "wb") as f:
            for chunk in resp.iter_content(8192):
                f.write(chunk)

        size_mb = os.path.getsize(raw_path) / (1024 * 1024)
        print(f"   📦 Tamanho do vídeo: {size_mb:.1f}MB (limite: {max_mb}MB)")
        if size_mb <= max_mb:
            print("   ✅ Vídeo dentro do limite — sem compressão necessária")
            return raw_path

        compressed_path = os.path.join(UPLOAD_DIR, f"{job_id}_compressed_clip.mp4")
        duration = _get_video_duration(raw_path) or 5.0
        target_kbps = max(700, int((max_mb * 8 * 1024) / max(duration, 1) * 0.80))
        print(f"   🗜️ Comprimindo: {size_mb:.1f}MB → ~{max_mb}MB (bitrate alvo: {target_kbps}kbps)...")

        result = subprocess.run(
            [
                "ffmpeg", "-y", "-i", raw_path,
                "-vf", "scale='min(1280,iw)':-2,fps=24",
                "-c:v", "libx264", "-preset", "veryfast", "-b:v", f"{target_kbps}k", "-maxrate", f"{target_kbps}k", "-bufsize", f"{target_kbps*2}k",
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
            print(f"   ✅ Comprimido: {size_mb:.1f}MB → {new_mb:.1f}MB")
            try:
                os.remove(raw_path)
            except OSError:
                pass
            return compressed_path

        print(f"   ⚠️ Compressão falhou: {result.stderr[-200:]}")
        return raw_path
    except Exception as e:
        print(f"   ❌ Erro ao baixar/comprimir vídeo: {e}")
        return None


def _upload_face_imgbb(face_path: str) -> Optional[str]:
    import base64

    try:
        with open(face_path, "rb") as f:
            b64 = base64.b64encode(f.read()).decode()
        session = _safe_session()
        resp = session.post(
            f"https://api.imgbb.com/1/upload?key={IMGBB_KEY}",
            data={"image": b64, "name": f"clipvox_face_{int(time.time())}"},
            timeout=(10, 60),
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
    )


def _upload_audio_to_r2(audio_path: str, job_id: str = "") -> Optional[str]:
    try:
        r2_client = get_r2_client()
        filename = os.path.basename(audio_path)
        r2_key = f"audio/{job_id}/{filename}"
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
        print(f"   📤 Upload áudio → R2: {filename}")
        with open(audio_path, "rb") as f:
            r2_client.put_object(
                Bucket=R2_BUCKET_NAME,
                Key=r2_key,
                Body=f,
                ContentType=content_type,
            )
        public_url = f"{R2_PUBLIC_URL}/{r2_key}"
        print(f"   ✅ Áudio no R2: {public_url}")
        return public_url
    except Exception as e:
        print(f"   ❌ Erro upload áudio R2: {e}")
        return None


def _check_url_accessible(url: str, label: str) -> bool:
    try:
        session = _safe_session()
        resp = session.head(url, timeout=(10, 30), allow_redirects=True)
        status = resp.status_code
        if status == 200:
            print(f"   ✅ {label} acessível (HTTP {status})")
            return True
        if status in (403, 405):
            resp = session.get(url, timeout=(10, 30), allow_redirects=True, stream=True)
            status = resp.status_code
            if status == 200:
                print(f"   ✅ {label} acessível via GET (HTTP {status})")
                return True
        print(f"   ❌ {label} NÃO acessível (HTTP {status}) — Kling pode falhar!")
        print(f"      URL: {url}")
        return False
    except Exception as e:
        print(f"   ⚠️ {label} — erro ao verificar: {e}")
        return False


def create_lipsync_task(video_url: str, audio_url: str, model: str = "kling", origin_task_id: str = "") -> Dict[str, Any]:
    print("🎤 Criando task de Lip Sync via PiAPI...")
    print(f"   Vídeo      : {video_url[:80]}")
    print(f"   Áudio      : {audio_url[:80]}")

    if origin_task_id:
        print(f"   🎯 Usando origin_task_id (sem download externo): {origin_task_id}")
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
        session = _safe_session()
        resp = session.post(
            f"{PIAPI_BASE}/api/v1/task",
            headers=_auth_headers(),
            json=payload,
            timeout=(10, 180),
        )
        print(f"   📥 HTTP {resp.status_code}: {resp.text[:300]}")
        data = resp.json()

        if data.get("code") != 200:
            raw_msg = (
                data.get("data", {}).get("error", {}).get("raw_message", "")
                or data.get("message", "sem mensagem")
            )
            error_type = _classify_error(raw_msg)
            print(f"   ❌ Erro PiAPI code: {data.get('code')}")
            print(f"   ❌ message : {data.get('message')}")
            print("   ❌ raw_message COMPLETO:")
            for i in range(0, len(raw_msg), 200):
                print(f"      {raw_msg[i:i+200]}")
            return _error_result(raw_msg or "Falha ao criar task de lip sync", raw_msg=raw_msg, error_type=error_type)

        task_id = data.get("data", {}).get("task_id")
        print(f"   ✅ Task criada: {task_id}")
        return {"success": True, "task_id": task_id}
    except requests.exceptions.ReadTimeout as e:
        return _error_result("Read timed out ao criar task de lip sync", raw_error=str(e), error_type="timeout")
    except Exception as e:
        print(f"   ❌ Exceção PiAPI: {e}")
        return _error_result("Exceção ao criar task de lip sync", raw_error=str(e))


def poll_lipsync_task(task_id: str, timeout: int = 600) -> Dict[str, Any]:
    print(f"   ⏳ Aguardando lip sync (task {task_id})...")
    session = _safe_session()

    for elapsed in range(15, timeout + 1, 15):
        time.sleep(15)
        try:
            resp = session.get(
                f"{PIAPI_BASE}/api/v1/task/{task_id}",
                headers=_auth_headers(),
                timeout=(10, 60),
            )
            data = resp.json()
            task = data.get("data", {})
            status = task.get("status", "")
            print(f"   ⏳ Status: {status} ({elapsed}s)")

            if status == "completed":
                works = task.get("output", {}).get("works", [])
                if works:
                    url = works[0].get("video", {}).get("resource")
                    if url:
                        print(f"   ✅ Lip sync pronto: {url[:80]}")
                        return {"success": True, "video_url": url}
                return _error_result("Nenhum vídeo no resultado do lip sync")

            if status == "failed":
                error = task.get("error", {})
                raw_msg = error.get("raw_message", "") or error.get("message", "desconhecido")
                error_type = _classify_error(raw_msg)
                print("   ❌ Lip sync falhou — raw_message COMPLETO:")
                for i in range(0, max(len(raw_msg), 1), 200):
                    print(f"      {raw_msg[i:i+200]}")
                return _error_result(raw_msg or "Falha no polling do lip sync", raw_error=raw_msg, error_type=error_type)
        except requests.exceptions.ReadTimeout as e:
            print(f"   ⚠️ Polling timeout transitório: {e}")
            continue
        except Exception as e:
            print(f"   ⚠️ Polling erro: {e}")
            continue

    print(f"   ❌ Timeout ({timeout}s)")
    return _error_result(f"Timeout ({timeout}s) aguardando lip sync", error_type="timeout")


def _upload_lipsync_to_r2(video_url: str, job_id: str) -> Optional[str]:
    try:
        session = _safe_session()
        resp = session.get(video_url, timeout=(10, 120), stream=True)
        if resp.status_code != 200:
            return None
        from config import UPLOAD_DIR
        local_path = os.path.join(UPLOAD_DIR, f"{job_id}_lipsync.mp4")
        with open(local_path, "wb") as f:
            for chunk in resp.iter_content(8192):
                f.write(chunk)
        r2_client = get_r2_client()
        r2_key = f"lipsync/{job_id}/lipsync.mp4"
        with open(local_path, "rb") as f:
            r2_client.put_object(Bucket=R2_BUCKET_NAME, Key=r2_key, Body=f, ContentType="video/mp4")
        r2_url = f"{R2_PUBLIC_URL}/{r2_key}"
        print(f"   ✅ Lip sync no R2: {r2_url}")
        return r2_url
    except Exception as e:
        print(f"   ⚠️ Erro salvar lip sync R2: {e}")
        return None


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
) -> dict:
    audio_path = _convert_to_mp3(audio_source, job_id)

    if preextracted_vocals and os.path.isfile(preextracted_vocals):
        print(f"   🎵 Usando vocals pré-extraídos: {os.path.basename(preextracted_vocals)}")
        audio_path = _convert_to_mp3(preextracted_vocals, f"{job_id}_vocals")

    duration = clip_duration
    if not duration and not os.path.isfile(face_source):
        print("   🔍 Detectando duração do vídeo via ffprobe...")
        duration = _get_video_duration(face_source)

    if duration and duration > 0:
        audio_path = _trim_audio(audio_path, duration, job_id)
    else:
        print("   ⚠️ Duração do vídeo não detectada — enviando áudio sem trim")

    face_url = face_source
    original_face_url = face_source
    compressed_mode = False

    if origin_task_id:
        print("   🎯 origin_task_id disponível — pulando download/compressão")
        face_url = face_source
    elif os.path.isfile(face_source):
        print("   📤 Hospedando imagem de rosto no imgbb...")
        face_url = _upload_face_imgbb(face_source)
        if not face_url:
            return _error_result("Falha ao hospedar imagem do rosto", error_type="asset")
    else:
        print("   🔍 Verificando tamanho do vídeo (limite Kling: 10MB)...")
        size_mb = 0.0
        try:
            session = _safe_session()
            size_resp = session.head(face_source, timeout=(10, 30), allow_redirects=True)
            content_length = int(size_resp.headers.get("Content-Length", 0) or 0)
            if content_length > 0:
                size_mb = content_length / (1024 * 1024)
                print(f"   📦 Tamanho estimado: {size_mb:.1f}MB")
            else:
                print("   ⚠️ Content-Length ausente — faremos validação via download só se necessário")
        except Exception as e:
            print(f"   ⚠️ Falha ao verificar tamanho via HEAD: {e}")

        if size_mb > 9 or size_mb == 0:
            print("   🗜️ Validando/comprimindo vídeo e hospedando no R2...")
            local_video = _download_and_compress_video(face_source, job_id, max_mb=7)
            if local_video:
                compressed_mode = local_video.endswith("_compressed_clip.mp4") or os.path.getsize(local_video) > 0
                r2_client = get_r2_client()
                r2_key = f"clips/{job_id}/compressed_clip.mp4"
                with open(local_video, "rb") as f:
                    r2_client.put_object(Bucket=R2_BUCKET_NAME, Key=r2_key, Body=f, ContentType="video/mp4")
                face_url = f"{R2_PUBLIC_URL}/{r2_key}"
                print(f"   ✅ Vídeo preparado no R2: {face_url}")
                try:
                    os.remove(local_video)
                except OSError:
                    pass
            else:
                print("   ⚠️ Compressão falhou — usando URL original")
                face_url = original_face_url
        else:
            print("   ✅ Vídeo dentro do limite — usando URL original do Kling")

    print("   📤 Hospedando áudio no Cloudflare R2...")
    audio_url = _upload_audio_to_r2(audio_path, job_id)
    if not audio_url:
        return _error_result("Falha ao hospedar áudio no R2", error_type="asset")

    print("\n🔍 Verificando acessibilidade das URLs para o Kling...")
    video_ok = True if origin_task_id else _check_url_accessible(face_url, "Vídeo")
    audio_ok = _check_url_accessible(audio_url, "Áudio (R2)")
    if not video_ok:
        return _error_result(f"URL do vídeo não acessível: {face_url[:120]}", error_type="asset")
    if not audio_ok:
        return _error_result(f"URL do áudio R2 não acessível: {audio_url[:120]}", error_type="asset")

    last_error = _error_result("Lip sync falhou sem detalhe")
    for attempt in range(1, max_retries + 1):
        print(f"\n🎤 Lip Sync — Tentativa {attempt}/{max_retries}")

        if origin_task_id:
            current_face_url = face_url
            print("   🎯 origin_task_id disponível — mantendo mesmo modo em todas as tentativas")
        elif compressed_mode:
            current_face_url = face_url
            print("   🔒 Vídeo comprimido detectado — mantendo URL R2 em todas as tentativas")
        elif attempt == 1:
            current_face_url = face_url
        elif attempt == 2:
            current_face_url = original_face_url
            if face_url != original_face_url:
                print("   🔄 Tentativa 2: usando URL original do Kling CDN")
        else:
            current_face_url = face_url
            print("   🔄 Tentativa 3: retry com URL R2")

        create_result = create_lipsync_task(
            current_face_url,
            audio_url,
            model,
            origin_task_id=origin_task_id or "",
        )
        if not create_result.get("success"):
            last_error = create_result
            delay = 20 * attempt
            print(f"   ⏳ Aguardando {delay}s antes de tentar novamente...")
            time.sleep(delay)
            continue

        task_id = create_result["task_id"]
        poll_result = poll_lipsync_task(task_id)
        if poll_result.get("success"):
            video_url = poll_result["video_url"]
            r2_url = _upload_lipsync_to_r2(video_url, job_id)
            return {
                "success": True,
                "video_url": r2_url or video_url,
                "task_id": task_id,
            }

        last_error = poll_result
        if poll_result.get("error_type") == "no_face":
            print("   ❌ Falha facial (609/no_face) — não adianta insistir igual")
            break

        delay = 30 * attempt
        print(f"   ⏳ Aguardando {delay}s antes de tentar novamente...")
        time.sleep(delay)

    print(f"   ❌ Lip sync falhou após {max_retries} tentativas — clipe será usado sem sincronização")
    return _error_result(
        last_error.get("error", f"Lip sync falhou após {max_retries} tentativas"),
        raw_error=last_error.get("raw_error", last_error.get("error", "")),
        error_type=last_error.get("error_type", "unknown"),
    )
