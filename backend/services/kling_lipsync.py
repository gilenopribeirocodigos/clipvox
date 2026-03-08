"""
🎤 ClipVox - Kling AI Lip Sync Service (via PiAPI)
Fluxo:
  1. Extrai vocals da música com LALAL.AI (remove instrumentos)
  2. Faz upload dos vocals para Cloudflare R2
  3. Envia para PiAPI (Kling lip sync)
  4. Faz polling até concluir
  5. Salva resultado no R2 e retorna a URL
Auth: x-api-key (PIAPI_API_KEY)
"""

import os
import time
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
        ct_map    = {"mp3": "audio/mpeg", "wav": "audio/wav",
                     "ogg": "audio/ogg",  "m4a": "audio/mp4",
                     "aac": "audio/aac",  "flac": "audio/flac"}
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
# PIAPI LIP SYNC — criar task
# ═══════════════════════════════════════════════════════════════
def create_lipsync_task(video_url: str, audio_url: str,
                        model: str = "kling-v1-6") -> Optional[str]:
    print(f"🎤 Criando task de Lip Sync via PiAPI...")
    print(f"   Vídeo      : {video_url[:80]}")
    print(f"   Áudio      : {audio_url[:80]}")

    # PiAPI: mesmo endpoint /api/v1/task, task_type "lip_sync"
    payload = {
        "model":     model,
        "task_type": "lip_sync",
        "input": {
            "video_url":         video_url,
            "local_dubbing_url": audio_url,  # PiAPI usa local_dubbing_url (não "voice")
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
        print(f"   📥 HTTP {resp.status_code}: {resp.text[:400]}")
        data = resp.json()

        if data.get("code") != 200:
            print(f"   ❌ Erro PiAPI: {data.get('message')}")
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
            resp = requests.get(
                f"{PIAPI_BASE}/api/v1/task/{task_id}",
                headers=_auth_headers(),
                timeout=15,
            )
            data   = resp.json()
            task   = data.get("data", {})
            # PiAPI usa "status": pending | processing | completed | failed
            status = task.get("status", "")
            print(f"   ⏳ Status: {status} ({elapsed}s)")

            if status == "completed":
                # URL em: data.output.works[0].video.resource
                works = task.get("output", {}).get("works", [])
                if works:
                    url = works[0].get("video", {}).get("resource")
                    if url:
                        print(f"   ✅ Lip sync pronto: {url[:80]}")
                        return url
                print(f"   ❌ Nenhum vídeo no resultado")
                return None

            elif status == "failed":
                error = task.get("error", {}).get("message", "desconhecido")
                print(f"   ❌ Lip sync falhou: {error}")
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
    face_source:  str,
    audio_source: str,
    job_id:       str  = "",
    model:        str  = "kling-v1-6",
    max_retries:  int  = 2,
    extract_vocals_first: bool = True,
) -> dict:
    """
    face_source  : caminho local ou URL de um vídeo MP4 com o rosto
    audio_source : caminho local do áudio da música
    extract_vocals_first: se True, extrai só a voz com LALAL.AI antes do lip sync
    """

    # ── Extrair vocals com LALAL.AI ───────────────────────────────────────────
    audio_path = audio_source
    if extract_vocals_first and os.path.isfile(audio_source):
        from services.lalal_vocals import extract_vocals
        print(f"🎵 Extraindo vocals com LALAL.AI para melhorar lip sync...")
        vocals_path = extract_vocals(audio_source, job_id)
        if vocals_path:
            audio_path = vocals_path
            print(f"   ✅ Usando vocals isolados: {os.path.basename(vocals_path)}")
        else:
            print(f"   ⚠️ LALAL.AI falhou — usando áudio original")

    # ── Resolver URL do rosto ─────────────────────────────────────────────────
    face_url = face_source
    if os.path.isfile(face_source):
        print(f"   📤 Hospedando rosto no imgbb...")
        face_url = _upload_face_imgbb(face_source)
        if not face_url:
            return {"success": False, "error": "Falha ao hospedar imagem do rosto"}

    # ── Upload do áudio para R2 ───────────────────────────────────────────────
    print(f"   📤 Hospedando áudio no Cloudflare R2...")
    audio_url = _upload_audio_to_r2(audio_path, job_id)
    if not audio_url:
        return {"success": False, "error": "Falha ao hospedar áudio no R2"}

    # ── Tentativas de lip sync ────────────────────────────────────────────────
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
