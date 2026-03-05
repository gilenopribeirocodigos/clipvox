"""
🎤 ClipVox - Kling AI Lip Sync Service (v2 — com extração de vocals via LALAL.AI)
Fluxo:
  1. Extrai vocals da música com LALAL.AI (remove instrumentos)
  2. Faz upload da imagem/vídeo do rosto para imgbb
  3. Faz upload dos vocals para Cloudflare R2
  4. Envia para a API do Kling lip sync
  5. Faz polling até concluir
  6. Retorna a URL do vídeo com lip sync
"""

import os
import time
import jwt
import requests
import boto3
from typing import Optional

KLING_ACCESS_KEY = os.getenv("KLING_ACCESS_KEY", "")
KLING_SECRET_KEY = os.getenv("KLING_SECRET_KEY", "")
KLING_API_BASE   = "https://api.klingai.com"
IMGBB_KEY        = os.getenv("IMGBB_API_KEY", "")
R2_ACCESS_KEY    = os.getenv("R2_ACCESS_KEY_ID", "")
R2_SECRET_KEY    = os.getenv("R2_SECRET_ACCESS_KEY", "")
R2_ENDPOINT      = os.getenv("R2_ENDPOINT_URL", "")
R2_BUCKET_NAME   = os.getenv("R2_BUCKET_NAME", "clipvox-images")
R2_PUBLIC_URL    = os.getenv("R2_PUBLIC_URL", "").rstrip("/")


# ═══════════════════════════════════════════════════════════════
# AUTH
# ═══════════════════════════════════════════════════════════════
def _auth_headers() -> dict:
    payload = {
        "iss": KLING_ACCESS_KEY,
        "exp": int(time.time()) + 1800,
        "nbf": int(time.time()) - 5,
    }
    token = jwt.encode(payload, KLING_SECRET_KEY, algorithm="HS256",
                       headers={"alg": "HS256", "typ": "JWT"})
    return {"Content-Type": "application/json", "Authorization": f"Bearer {token}"}


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
# KLING LIP SYNC — criar task
# ═══════════════════════════════════════════════════════════════
def create_lipsync_task(video_url: str, audio_url: str,
                        model: str = "kling-v1-6") -> Optional[str]:
    print(f"🎤 Criando task de Lip Sync...")
    print(f"   Personagem : {video_url[:80]}")
    print(f"   Áudio      : {audio_url[:80]}")

    payload = {
        "model_name": model,
        "input": {
            "video_url":  video_url,
            "voice":      audio_url,
            "voice_type": "audio",
            "mode":       "audio2video",
        }
    }
    try:
        resp = requests.post(
            f"{KLING_API_BASE}/v1/videos/lip-sync",
            headers=_auth_headers(),
            json=payload,
            timeout=30,
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
        print(f"   ❌ Exceção Kling: {e}")
        return None


# ═══════════════════════════════════════════════════════════════
# KLING LIP SYNC — polling
# ═══════════════════════════════════════════════════════════════
def poll_lipsync_task(task_id: str, timeout: int = 600) -> Optional[str]:
    print(f"   ⏳ Aguardando lip sync (task {task_id})...")
    for elapsed in range(15, timeout + 1, 15):
        time.sleep(15)
        try:
            resp = requests.get(
                f"{KLING_API_BASE}/v1/videos/lip-sync/{task_id}",
                headers=_auth_headers(),
                timeout=15,
            )
            data   = resp.json()
            status = data.get("data", {}).get("task_status", "")
            print(f"   ⏳ Status: {status} ({elapsed}s)")
            if status == "succeed":
                videos = data.get("data", {}).get("task_result", {}).get("videos", [])
                if videos:
                    url = videos[0].get("url")
                    print(f"   ✅ Lip sync pronto: {url[:80]}")
                    return url
                return None
            elif status == "failed":
                print(f"   ❌ Lip sync falhou: {data.get('data', {}).get('task_status_msg')}")
                return None
        except Exception as e:
            print(f"   ⚠️ Polling erro: {e}")
    print(f"   ❌ Timeout ({timeout}s)")
    return None


# ═══════════════════════════════════════════════════════════════
# UPLOAD VIDEO LIP SYNC → R2
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
            # Salvar no R2 para persistência
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
