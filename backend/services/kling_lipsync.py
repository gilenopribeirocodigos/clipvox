"""
🎤 ClipVox - Kling Lip Sync Service
─────────────────────────────────────────────────────────────────
Gera vídeo com sincronização labial usando Kling AI.

FLUXO:
  foto do personagem (imgbb) + áudio da música (Cloudflare R2)
        ↓
  Kling AI Lip Sync
        ↓
  vídeo do personagem cantando sincronizado

Auth: JWT (mesmo padrão do kling_video.py)
"""

import os
import time
import base64
import requests
import jwt
from typing import Optional

from config import (
    R2_BUCKET_NAME,
    R2_PUBLIC_URL,
    get_r2_client,
    UPLOAD_DIR,
)

KLING_ACCESS_KEY = os.getenv("KLING_ACCESS_KEY", "")
KLING_SECRET_KEY = os.getenv("KLING_SECRET_KEY", "")
KLING_API_BASE   = "https://api.klingai.com"
IMGBB_KEY        = os.getenv("IMGBB_API_KEY", "")


def _get_jwt_token() -> str:
    if not KLING_ACCESS_KEY or not KLING_SECRET_KEY:
        raise ValueError("KLING_ACCESS_KEY e KLING_SECRET_KEY são obrigatórios")
    headers = {"alg": "HS256", "typ": "JWT"}
    payload = {
        "iss": KLING_ACCESS_KEY,
        "exp": int(time.time()) + 1800,
        "nbf": int(time.time()) - 5
    }
    return jwt.encode(payload, KLING_SECRET_KEY, algorithm="HS256", headers=headers)


def _auth_headers() -> dict:
    return {
        "Content-Type":  "application/json",
        "Authorization": f"Bearer {_get_jwt_token()}"
    }


# ── imgbb → apenas imagens ────────────────────────────────────────────────────
def _upload_image_to_imgbb(image_path: str) -> Optional[str]:
    if not IMGBB_KEY:
        print("   ⚠️ IMGBB_API_KEY não configurada")
        return None
    try:
        with open(image_path, "rb") as f:
            b64 = base64.b64encode(f.read()).decode("utf-8")
        resp = requests.post(
            f"https://api.imgbb.com/1/upload?key={IMGBB_KEY}",
            data={"image": b64, "name": f"clipvox_face_{int(time.time())}"},
            timeout=60
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


# ── R2 → áudio (imgbb NÃO aceita áudio) ──────────────────────────────────────
def _upload_audio_to_r2(audio_path: str, job_id: str = "") -> Optional[str]:
    try:
        r2_client = get_r2_client()
        if not r2_client:
            print("   ❌ R2 não configurado")
            return None

        filename = os.path.basename(audio_path)
        ext      = filename.rsplit(".", 1)[-1].lower()
        r2_key   = f"audio/{job_id}/{filename}" if job_id else f"audio/{filename}"

        content_types = {
            "mp3": "audio/mpeg", "wav": "audio/wav",
            "ogg": "audio/ogg",  "m4a": "audio/mp4",
            "aac": "audio/aac",  "flac": "audio/flac",
        }
        content_type = content_types.get(ext, "audio/mpeg")

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


def create_lipsync_task(video_url: str, audio_url: str, model: str = "kling-v1-6") -> Optional[str]:
    print(f"\n🎤 Criando task de Lip Sync...")
    print(f"   Personagem : {video_url[:80]}")
    print(f"   Áudio      : {audio_url[:80]}")

    if not KLING_ACCESS_KEY:
        print("   ❌ KLING_ACCESS_KEY não configurada")
        return None

    payload = {
        "model_name": model,
        "input": {
            "video":      video_url,
            "voice":      audio_url,
            "voice_type": "audio",
            "mode":       "audio2video",   # obrigatório pela API Kling lip sync
        }
    }

    try:
        resp = requests.post(
            f"{KLING_API_BASE}/v1/videos/lip-sync",
            headers=_auth_headers(),
            json=payload,
            timeout=30
        )
        print(f"   📥 HTTP {resp.status_code}: {resp.text[:400]}")
        data = resp.json()

        if data.get("code") != 0:
            print(f"   ❌ Erro Kling: {data.get('message')}")
            return None

        task_id = data.get("data", {}).get("task_id")
        print(f"   ✅ Task criada: {task_id}")
        return task_id

    except Exception as e:
        print(f"   ❌ Exceção: {e}")
        return None


def poll_lipsync_task(task_id: str, timeout: int = 600) -> Optional[str]:
    print(f"   ⏳ Polling lip sync {task_id}...")

    for elapsed in range(10, timeout + 1, 10):
        time.sleep(10)
        try:
            resp = requests.get(
                f"{KLING_API_BASE}/v1/videos/lip-sync/{task_id}",
                headers=_auth_headers(),
                timeout=15
            )
            data      = resp.json()

            if data.get("code") != 0:
                print(f"   ❌ Polling erro: {data.get('message')}")
                return None

            task_info = data.get("data", {})
            status    = task_info.get("task_status", "")
            print(f"   🔄 Status: {status} ({elapsed}s)")

            if status == "succeed":
                videos = task_info.get("task_result", {}).get("videos", [])
                if videos:
                    url = videos[0].get("url")
                    print(f"   ✅ Lip sync pronto: {url[:80]}")
                    return url
                print("   ❌ Nenhum vídeo no resultado")
                return None

            elif status == "failed":
                msg = task_info.get("task_status_msg", "")
                print(f"   ❌ Task falhou: {msg}")
                return None

        except Exception as e:
            print(f"   ⚠️ Polling erro: {e}")

    print(f"   ❌ Timeout ({timeout}s)")
    return None


def generate_lipsync(
    face_source:  str,
    audio_source: str,
    job_id:       str = "",
    model:        str = "kling-v1-6",
    max_retries:  int = 2,
) -> dict:
    """
    Orquestra o lip sync completo:
      1. Imagem do rosto → imgbb  (só imagens)
      2. Áudio           → R2     (imgbb não aceita áudio)
      3. Cria task Kling → polling → baixa vídeo
    """

    # ── Imagem do rosto ───────────────────────────────────────────────────────
    face_url = face_source
    if face_source and os.path.exists(face_source):
        print(f"   📤 Hospedando rosto no imgbb...")
        face_url = _upload_image_to_imgbb(face_source)
        if not face_url:
            return {"success": False, "error": "Falha ao hospedar imagem do personagem no imgbb"}

    # ── Áudio via R2 ──────────────────────────────────────────────────────────
    audio_url = audio_source
    if audio_source and os.path.exists(audio_source):
        print(f"   📤 Hospedando áudio no Cloudflare R2...")
        audio_url = _upload_audio_to_r2(audio_source, job_id)
        if not audio_url:
            return {
                "success": False,
                "error": (
                    "Falha ao hospedar áudio no R2. "
                    "Verifique R2_ACCESS_KEY_ID, R2_SECRET_ACCESS_KEY, "
                    "R2_ENDPOINT_URL e R2_PUBLIC_URL nas variáveis de ambiente."
                )
            }

    if not face_url or not audio_url:
        return {"success": False, "error": "face_source e audio_source são obrigatórios"}

    # ── Tentativas ────────────────────────────────────────────────────────────
    for attempt in range(1, max_retries + 1):
        print(f"\n🎤 Lip Sync — Tentativa {attempt}/{max_retries}")

        task_id = create_lipsync_task(
            video_url=face_url,
            audio_url=audio_url,
            model=model
        )

        if not task_id:
            time.sleep(15 * attempt)
            continue

        result_url = poll_lipsync_task(task_id)

        if result_url:
            local_path = _download_lipsync_video(result_url, job_id)
            return {
                "success":    True,
                "video_url":  result_url,
                "video_path": local_path,
                "task_id":    task_id,
                "attempt":    attempt,
            }

        time.sleep(20 * attempt)

    return {
        "success":   False,
        "video_url": None,
        "task_id":   None,
        "error":     f"Lip sync falhou após {max_retries} tentativas",
    }


def _download_lipsync_video(video_url: str, job_id: str) -> Optional[str]:
    try:
        resp = requests.get(video_url, timeout=120, stream=True)
        if resp.status_code != 200:
            return None
        filename   = f"lipsync_{job_id}.mp4" if job_id else f"lipsync_{int(time.time())}.mp4"
        local_path = os.path.join(UPLOAD_DIR, filename)
        with open(local_path, "wb") as f:
            for chunk in resp.iter_content(chunk_size=8192):
                f.write(chunk)
        print(f"   💾 Lip sync salvo: {local_path}")
        return local_path
    except Exception as e:
        print(f"   ⚠️ Erro ao baixar vídeo lip sync: {e}")
        return None
