"""
🎤 ClipVox - Kling AI Lip Sync Service (via PiAPI)
Fluxo:
  1. Converte áudio para MP3 (compatível + leve) via ffmpeg
  2. ✅ NOVO: Trime o áudio para a duração exata do vídeo (ffprobe + ffmpeg)
  3. Extrai vocals da música com LALAL.AI (remove instrumentos)
  4. Faz upload dos vocals/áudio para Cloudflare R2
  5. Verifica acessibilidade pública das URLs antes de enviar ao Kling
  6. Envia para PiAPI (Kling lip sync)
  7. Faz polling até concluir
  8. Salva resultado no R2 e retorna a URL
Auth: x-api-key (PIAPI_API_KEY)
"""

import os
import time
import subprocess
import requests
import boto3
from typing import Optional

PIAPI_API_KEY  = os.getenv("PIAPI_API_KEY", "")
PIAPI_BASE     = "https://api.piapi.ai"
IMGBB_KEY      = os.getenv("IMGBB_API_KEY", "")
R2_ACCESS_KEY  = os.getenv("R2_ACCESS_KEY_ID", "")
R2_SECRET_KEY  = os.getenv("R2_SECRET_ACCESS_KEY", "")
R2_ENDPOINT    = os.getenv("R2_ENDPOINT_URL", "")
R2_BUCKET_NAME = os.getenv("R2_BUCKET_NAME", "clipvox-images")
R2_PUBLIC_URL  = os.getenv("R2_PUBLIC_URL", "").rstrip("/")


# ═══════════════════════════════════════════════════════════════
# AUTH
# ═══════════════════════════════════════════════════════════════
def _auth_headers() -> dict:
    if not PIAPI_API_KEY:
        raise ValueError("PIAPI_API_KEY não configurada")
    return {
        "Content-Type": "application/json",
        "x-api-key":    PIAPI_API_KEY,
    }


# ═══════════════════════════════════════════════════════════════
# DETECTAR DURAÇÃO DO VÍDEO VIA FFPROBE
# ═══════════════════════════════════════════════════════════════
def _get_video_duration(video_url: str) -> Optional[float]:
    """
    Usa ffprobe para detectar a duração do vídeo (em segundos).
    Funciona com URLs remotas (Kling CDN) ou caminhos locais.
    """
    try:
        result = subprocess.run([
            "ffprobe", "-v", "quiet",
            "-print_format", "json",
            "-show_format",
            video_url
        ], capture_output=True, text=True, timeout=30)

        if result.returncode == 0:
            import json
            info     = json.loads(result.stdout)
            duration = float(info.get("format", {}).get("duration", 0))
            if duration > 0:
                print(f"   ⏱️ Duração do vídeo detectada: {duration:.2f}s")
                return duration
        print(f"   ⚠️ ffprobe não retornou duração válida")
        return None
    except Exception as e:
        print(f"   ⚠️ ffprobe erro: {e}")
        return None


# ═══════════════════════════════════════════════════════════════
# CONVERTER ÁUDIO PARA MP3
# ═══════════════════════════════════════════════════════════════
def _convert_to_mp3(audio_path: str, job_id: str = "") -> str:
    """
    Converte qualquer áudio para MP3 128kbps via ffmpeg.
    Retorna o path do MP3 (ou o original se ffmpeg falhar).
    """
    ext = audio_path.rsplit(".", 1)[-1].lower()
    if ext == "mp3":
        return audio_path

    from config import UPLOAD_DIR
    mp3_filename = f"{job_id}_lipsync_audio.mp3" if job_id else f"lipsync_{int(time.time())}.mp3"
    mp3_path     = os.path.join(UPLOAD_DIR, mp3_filename)

    print(f"   🔄 Convertendo {ext.upper()} → MP3 para compatibilidade com Kling...")
    try:
        result = subprocess.run([
            "ffmpeg", "-y", "-i", audio_path,
            "-vn", "-ar", "44100", "-ac", "2", "-b:a", "128k",
            mp3_path
        ], capture_output=True, text=True, timeout=120)

        if result.returncode == 0 and os.path.exists(mp3_path):
            original_size = os.path.getsize(audio_path) // 1024
            mp3_size      = os.path.getsize(mp3_path) // 1024
            print(f"   ✅ Convertido: {original_size}KB → {mp3_size}KB MP3")
            return mp3_path
        else:
            print(f"   ⚠️ ffmpeg falhou ({result.stderr[-200:]}), usando original")
            return audio_path
    except Exception as e:
        print(f"   ⚠️ Erro conversão MP3: {e}, usando original")
        return audio_path


# ═══════════════════════════════════════════════════════════════
# ✅ NOVO: TRIMAR ÁUDIO PARA DURAÇÃO DO CLIPE
# ═══════════════════════════════════════════════════════════════
def _trim_audio(audio_path: str, duration: float, job_id: str = "") -> str:
    """
    Trime o áudio para a duração exata do vídeo (em segundos).
    Kling rejeita quando o áudio é muito mais longo que o vídeo.
    Retorna o path do áudio trimado (ou original se falhar).
    """
    try:
        audio_duration = _get_audio_duration(audio_path)
        if audio_duration and audio_duration <= duration + 0.5:
            print(f"   ✅ Áudio ({audio_duration:.1f}s) ≤ vídeo ({duration:.1f}s) — sem trim necessário")
            return audio_path

        from config import UPLOAD_DIR
        ext          = audio_path.rsplit(".", 1)[-1].lower()
        trimmed_path = os.path.join(UPLOAD_DIR, f"{job_id}_trimmed.{ext}")

        print(f"   ✂️ Trimando áudio: {audio_duration:.1f}s → {duration:.1f}s (duração do clipe)")
        result = subprocess.run([
            "ffmpeg", "-y",
            "-i", audio_path,
            "-t", str(duration),
            "-c", "copy",
            trimmed_path
        ], capture_output=True, text=True, timeout=60)

        if result.returncode == 0 and os.path.exists(trimmed_path):
            trimmed_size = os.path.getsize(trimmed_path) // 1024
            print(f"   ✅ Áudio trimado: {trimmed_size}KB ({duration:.1f}s)")
            return trimmed_path
        else:
            print(f"   ⚠️ Trim falhou: {result.stderr[-200:]}")
            return audio_path
    except Exception as e:
        print(f"   ⚠️ Erro ao trimar áudio: {e}")
        return audio_path


def _get_audio_duration(audio_path: str) -> Optional[float]:
    """Detecta duração do áudio local via ffprobe."""
    try:
        result = subprocess.run([
            "ffprobe", "-v", "quiet",
            "-print_format", "json",
            "-show_format",
            audio_path
        ], capture_output=True, text=True, timeout=15)
        if result.returncode == 0:
            import json
            info = json.loads(result.stdout)
            return float(info.get("format", {}).get("duration", 0))
        return None
    except Exception:
        return None


# ═══════════════════════════════════════════════════════════════
# ✅ NOVO: BAIXAR E COMPRIMIR VÍDEO SE > 10MB (limite Kling lip sync)
# ═══════════════════════════════════════════════════════════════
def _download_and_compress_video(video_url: str, job_id: str,
                                 max_mb: int = 9) -> Optional[str]:
    """
    Baixa o vídeo da URL e comprime para ficar abaixo de max_mb.
    Retorna path local do vídeo comprimido, ou None se falhar.
    O Kling aceita no máximo 10MB — usamos 9MB como margem de segurança.
    """
    from config import UPLOAD_DIR
    try:
        print(f"   📥 Baixando vídeo para verificar tamanho...")
        resp = requests.get(video_url, timeout=120, stream=True)
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
            print(f"   ✅ Vídeo dentro do limite — sem compressão necessária")
            return raw_path

        # Comprimir para ficar abaixo do limite
        compressed_path = os.path.join(UPLOAD_DIR, f"{job_id}_compressed_clip.mp4")
        duration        = _get_video_duration(raw_path) or 5.0
        target_kbps     = int((max_mb * 8 * 1024) / duration * 0.85)
        print(f"   🗜️ Comprimindo: {size_mb:.1f}MB → ~{max_mb}MB (bitrate alvo: {target_kbps}kbps)...")

        result = subprocess.run([
            "ffmpeg", "-y", "-i", raw_path,
            "-c:v", "libx264",
            "-b:v", f"{target_kbps}k",
            "-c:a", "copy",
            "-movflags", "+faststart",
            compressed_path
        ], capture_output=True, text=True, timeout=120)

        if result.returncode == 0 and os.path.exists(compressed_path):
            new_mb = os.path.getsize(compressed_path) / (1024 * 1024)
            print(f"   ✅ Comprimido: {size_mb:.1f}MB → {new_mb:.1f}MB")
            os.remove(raw_path)
            return compressed_path
        else:
            print(f"   ⚠️ Compressão falhou: {result.stderr[-200:]} — usando original")
            return raw_path

    except Exception as e:
        print(f"   ❌ Erro ao baixar/comprimir vídeo: {e}")
        return None


# ═══════════════════════════════════════════════════════════════
# UPLOAD FACE → imgbb
# ═══════════════════════════════════════════════════════════════
def _upload_face_imgbb(face_path: str) -> Optional[str]:
    import base64
    try:
        with open(face_path, "rb") as f:
            b64 = base64.b64encode(f.read()).decode()
        resp = requests.post(
            f"https://api.imgbb.com/1/upload?key={IMGBB_KEY}",
            data={"image": b64, "name": f"clipvox_face_{int(time.time())}"},
            timeout=60,
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


# ═══════════════════════════════════════════════════════════════
# UPLOAD AUDIO → Cloudflare R2
# ═══════════════════════════════════════════════════════════════
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
        filename  = os.path.basename(audio_path)
        r2_key    = f"audio/{job_id}/{filename}"
        ext       = filename.rsplit(".", 1)[-1].lower()
        ct_map    = {
            "mp3": "audio/mpeg", "wav": "audio/wav",
            "ogg": "audio/ogg",  "m4a": "audio/mp4",
            "aac": "audio/aac",  "flac": "audio/flac",
        }
        content_type = ct_map.get(ext, "audio/mpeg")
        print(f"   📤 Upload áudio → R2: {filename}")
        with open(audio_path, "rb") as f:
            r2_client.put_object(
                Bucket=R2_BUCKET_NAME, Key=r2_key,
                Body=f, ContentType=content_type,
            )
        public_url = f"{R2_PUBLIC_URL}/{r2_key}"
        print(f"   ✅ Áudio no R2: {public_url}")
        return public_url
    except Exception as e:
        print(f"   ❌ Erro upload áudio R2: {e}")
        return None


# ═══════════════════════════════════════════════════════════════
# VERIFICAR ACESSIBILIDADE DAS URLS
# ═══════════════════════════════════════════════════════════════
def _check_url_accessible(url: str, label: str) -> bool:
    try:
        resp   = requests.head(url, timeout=15, allow_redirects=True)
        status = resp.status_code
        if status == 200:
            print(f"   ✅ {label} acessível (HTTP {status})")
            return True
        else:
            print(f"   ❌ {label} NÃO acessível (HTTP {status}) — Kling vai falhar!")
            print(f"      URL: {url}")
            return False
    except Exception as e:
        print(f"   ⚠️ {label} — erro ao verificar: {e}")
        return False


# ═══════════════════════════════════════════════════════════════
# PIAPI LIP SYNC — criar task
# ═══════════════════════════════════════════════════════════════
def create_lipsync_task(video_url: str, audio_url: str,
                        model: str = "kling") -> Optional[str]:
    print(f"🎤 Criando task de Lip Sync via PiAPI...")
    print(f"   Vídeo      : {video_url[:80]}")
    print(f"   Áudio      : {audio_url[:80]}")

    payload = {
        "model":     model,
        "task_type": "lip_sync",
        "input": {
            "video_url":         video_url,
            "local_dubbing_url": audio_url,
            "tts_text":          "",
            "tts_timbre":        "",
            "tts_speed":         1,
        }
    }

    try:
        resp = requests.post(
            f"{PIAPI_BASE}/api/v1/task",
            headers=_auth_headers(),
            json=payload,
            timeout=30,
        )
        print(f"   📥 HTTP {resp.status_code}: {resp.text[:300]}")
        data = resp.json()

        if data.get("code") != 200:
            raw_msg = (
                data.get("data", {}).get("error", {}).get("raw_message", "")
                or data.get("message", "sem mensagem")
            )
            print(f"   ❌ Erro PiAPI code: {data.get('code')}")
            print(f"   ❌ message : {data.get('message')}")
            print(f"   ❌ raw_message COMPLETO:")
            for i in range(0, len(raw_msg), 200):
                print(f"      {raw_msg[i:i+200]}")
            return None

        task_id = data.get("data", {}).get("task_id")
        print(f"   ✅ Task criada: {task_id}")
        return task_id
    except Exception as e:
        print(f"   ❌ Exceção PiAPI: {e}")
        return None


# ═══════════════════════════════════════════════════════════════
# PIAPI LIP SYNC — polling
# ═══════════════════════════════════════════════════════════════
def poll_lipsync_task(task_id: str, timeout: int = 600) -> Optional[str]:
    print(f"   ⏳ Aguardando lip sync (task {task_id})...")

    for elapsed in range(15, timeout + 1, 15):
        time.sleep(15)
        try:
            resp   = requests.get(
                f"{PIAPI_BASE}/api/v1/task/{task_id}",
                headers=_auth_headers(),
                timeout=15,
            )
            data   = resp.json()
            task   = data.get("data", {})
            status = task.get("status", "")
            print(f"   ⏳ Status: {status} ({elapsed}s)")

            if status == "completed":
                works = task.get("output", {}).get("works", [])
                if works:
                    url = works[0].get("video", {}).get("resource")
                    if url:
                        print(f"   ✅ Lip sync pronto: {url[:80]}")
                        return url
                print(f"   ❌ Nenhum vídeo no resultado: {task.get('output')}")
                return None

            elif status == "failed":
                error     = task.get("error", {})
                raw_msg   = error.get("raw_message", "") or error.get("message", "desconhecido")
                print(f"   ❌ Lip sync falhou — raw_message COMPLETO:")
                for i in range(0, max(len(raw_msg), 1), 200):
                    print(f"      {raw_msg[i:i+200]}")
                return None

        except Exception as e:
            print(f"   ⚠️ Polling erro: {e}")

    print(f"   ❌ Timeout ({timeout}s)")
    return None


# ═══════════════════════════════════════════════════════════════
# UPLOAD RESULTADO LIP SYNC → R2
# ═══════════════════════════════════════════════════════════════
def _upload_lipsync_to_r2(video_url: str, job_id: str) -> Optional[str]:
    try:
        resp = requests.get(video_url, timeout=120, stream=True)
        if resp.status_code != 200:
            return None
        from config import UPLOAD_DIR
        local_path = os.path.join(UPLOAD_DIR, f"{job_id}_lipsync.mp4")
        with open(local_path, "wb") as f:
            for chunk in resp.iter_content(8192):
                f.write(chunk)
        r2_client = get_r2_client()
        r2_key    = f"lipsync/{job_id}/lipsync.mp4"
        with open(local_path, "rb") as f:
            r2_client.put_object(
                Bucket=R2_BUCKET_NAME, Key=r2_key,
                Body=f, ContentType="video/mp4",
            )
        r2_url = f"{R2_PUBLIC_URL}/{r2_key}"
        print(f"   ✅ Lip sync no R2: {r2_url}")
        return r2_url
    except Exception as e:
        print(f"   ⚠️ Erro salvar lip sync R2: {e}")
        return None


# ═══════════════════════════════════════════════════════════════
# FUNÇÃO PRINCIPAL
# ═══════════════════════════════════════════════════════════════
def generate_lipsync(
    face_source:          str,
    audio_source:         str,
    job_id:               str            = "",
    model:                str            = "kling",
    max_retries:          int            = 2,
    extract_vocals_first: bool           = True,
    clip_duration:        Optional[float] = None,
) -> dict:
    """
    face_source    : URL de vídeo do Kling CDN (kling_url) ou path local de imagem
    audio_source   : caminho local do áudio da música
    clip_duration  : duração do clipe em segundos (para trim do áudio)
                     Se None, detecta automaticamente via ffprobe na URL do vídeo
    """

    # ── 1. Converter áudio para MP3 ───────────────────────────────────────────
    audio_path = _convert_to_mp3(audio_source, job_id)

    # ── 2. Extrair vocals com LALAL.AI ────────────────────────────────────────
    if extract_vocals_first and os.path.isfile(audio_path):
        from services.lalal_vocals import extract_vocals
        print(f"🎵 Extraindo vocals com LALAL.AI para melhorar lip sync...")
        vocals_path = extract_vocals(audio_path, job_id)
        if vocals_path:
            audio_path = _convert_to_mp3(vocals_path, f"{job_id}_vocals")
            print(f"   ✅ Usando vocals isolados: {os.path.basename(audio_path)}")
        else:
            print(f"   ⚠️ LALAL.AI falhou — usando áudio original convertido")

    # ── 3. ✅ Trimar áudio para duração do clipe ──────────────────────────────
    # Detecta duração do vídeo automaticamente se não foi passada
    duration = clip_duration
    if not duration and not os.path.isfile(face_source):
        print(f"   🔍 Detectando duração do vídeo via ffprobe...")
        duration = _get_video_duration(face_source)

    if duration and duration > 0:
        audio_path = _trim_audio(audio_path, duration, job_id)
    else:
        print(f"   ⚠️ Duração do vídeo não detectada — enviando áudio sem trim")

    # ── 4. Resolver URL do rosto + compressão se > 10MB ─────────────────────
    face_url = face_source
    if os.path.isfile(face_source):
        # Imagem local → sobe no imgbb
        print(f"   📤 Hospedando rosto no imgbb...")
        face_url = _upload_face_imgbb(face_source)
        if not face_url:
            return {"success": False, "error": "Falha ao hospedar imagem do rosto"}
    else:
        # URL de vídeo → baixa, comprime se > 9MB, sobe no imgbb
        print(f"   🔍 Verificando tamanho do vídeo (limite Kling: 10MB)...")
        local_video = _download_and_compress_video(face_source, job_id, max_mb=9)
        if local_video:
            print(f"   📤 Hospedando vídeo no imgbb...")
            uploaded = _upload_face_imgbb(local_video)
            face_url = uploaded if uploaded else face_source
            if not uploaded:
                print(f"   ⚠️ imgbb falhou — tentando URL original do Kling")
        else:
            print(f"   ⚠️ Download/compressão falhou — tentando URL original")

    # ── 5. Upload do áudio para R2 ────────────────────────────────────────────
    print(f"   📤 Hospedando áudio no Cloudflare R2...")
    audio_url = _upload_audio_to_r2(audio_path, job_id)
    if not audio_url:
        return {"success": False, "error": "Falha ao hospedar áudio no R2"}

    # ── 6. Verificar acessibilidade ───────────────────────────────────────────
    print(f"\n🔍 Verificando acessibilidade das URLs para o Kling...")
    video_ok = _check_url_accessible(face_url,  "Vídeo (kling_url)")
    audio_ok = _check_url_accessible(audio_url, "Áudio (R2)")

    if not video_ok:
        return {"success": False, "error": f"URL do vídeo não acessível: {face_url[:100]}"}
    if not audio_ok:
        return {"success": False, "error": f"URL do áudio R2 não acessível: {audio_url[:100]}"}

    # ── 7. Tentativas de lip sync ─────────────────────────────────────────────
    for attempt in range(1, max_retries + 1):
        print(f"\n🎤 Lip Sync — Tentativa {attempt}/{max_retries}")
        task_id = create_lipsync_task(face_url, audio_url, model)
        if not task_id:
            delay = 15 * attempt
            print(f"   ⏳ Aguardando {delay}s antes de tentar novamente...")
            time.sleep(delay)
            continue

        video_url = poll_lipsync_task(task_id)
        if video_url:
            r2_url = _upload_lipsync_to_r2(video_url, job_id)
            return {
                "success":   True,
                "video_url": r2_url or video_url,
                "task_id":   task_id,
            }
        delay = 30 * attempt
        print(f"   ⏳ Aguardando {delay}s antes de tentar novamente...")
        time.sleep(delay)

    return {"success": False, "error": f"Lip sync falhou após {max_retries} tentativas"}
