"""
🎤 ClipVox - Kling Lip Sync Service
─────────────────────────────────────────────────────────────────
Gera vídeo com sincronização labial usando Kling AI.

FLUXO:
  foto do personagem (ou vídeo) + áudio da música
        ↓
  Kling AI Lip Sync
        ↓
  vídeo do personagem cantando sincronizado

Endpoint: POST /v1/videos/lip-sync
Auth: JWT (mesmo padrão do kling_video.py)
"""

import os
import time
import base64
import requests
import jwt
from typing import Optional

# ── Configurações (reutiliza as mesmas variáveis do kling_video.py) ───────────
KLING_ACCESS_KEY = os.getenv("KLING_ACCESS_KEY", "")
KLING_SECRET_KEY = os.getenv("KLING_SECRET_KEY", "")
KLING_API_BASE   = "https://api.klingai.com"
IMGBB_KEY        = os.getenv("IMGBB_API_KEY", "")


# ─────────────────────────────────────────────────────────────────────────────
# AUTH JWT (igual ao kling_video.py)
# ─────────────────────────────────────────────────────────────────────────────
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


# ─────────────────────────────────────────────────────────────────────────────
# UPLOAD IMAGEM/ÁUDIO PARA IMGBB (URL pública para o Kling consumir)
# ─────────────────────────────────────────────────────────────────────────────
def _upload_to_imgbb(file_path: str, label: str = "file") -> Optional[str]:
    """Faz upload de qualquer arquivo binário para imgbb e retorna URL pública."""
    if not IMGBB_KEY:
        print(f"   ⚠️ IMGBB_API_KEY não configurada — não foi possível hospedar {label}")
        return None
    try:
        with open(file_path, "rb") as f:
            b64 = base64.b64encode(f.read()).decode("utf-8")
        resp = requests.post(
            f"https://api.imgbb.com/1/upload?key={IMGBB_KEY}",
            data={"image": b64, "name": f"clipvox_{label}_{int(time.time())}"},
            timeout=60
        )
        if resp.status_code == 200:
            url = resp.json().get("data", {}).get("url")
            if url:
                time.sleep(2)
                print(f"   ✅ imgbb {label}: {url}")
                return url
        print(f"   ❌ imgbb falhou ({label}): HTTP {resp.status_code}")
        return None
    except Exception as e:
        print(f"   ❌ imgbb erro ({label}): {e}")
        return None


# ─────────────────────────────────────────────────────────────────────────────
# CRIAR TASK DE LIP SYNC
# ─────────────────────────────────────────────────────────────────────────────
def create_lipsync_task(
    video_url:  str,          # URL do vídeo/imagem do personagem
    audio_url:  str,          # URL do áudio (mp3/wav)
    model:      str = "kling-v1-6",
) -> Optional[str]:
    """
    Envia requisição de lip sync para a Kling AI.
    Retorna o task_id ou None se falhar.
    
    - video_url : URL pública do vídeo (ou imagem) com o rosto do personagem
    - audio_url : URL pública do áudio da música
    """
    print(f"\n🎤 Criando task de Lip Sync...")
    print(f"   Personagem: {video_url[:80]}")
    print(f"   Áudio:      {audio_url[:80]}")

    if not KLING_ACCESS_KEY:
        print("   ❌ KLING_ACCESS_KEY não configurada")
        return None

    payload = {
        "model_name": model,
        "input": {
            "video":      video_url,   # rosto do personagem
            "voice":      audio_url,   # música
            "voice_type": "audio",     # "audio" = URL de áudio; "text" = TTS
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
        print(f"   ❌ Exceção ao criar task: {e}")
        return None


# ─────────────────────────────────────────────────────────────────────────────
# POLLING ATÉ O VÍDEO FICAR PRONTO
# ─────────────────────────────────────────────────────────────────────────────
def poll_lipsync_task(task_id: str, timeout: int = 600) -> Optional[str]:
    """
    Verifica periodicamente o status da task.
    Retorna a URL do vídeo final quando pronto, ou None.
    """
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


# ─────────────────────────────────────────────────────────────────────────────
# FUNÇÃO PRINCIPAL — gera lip sync de uma imagem/vídeo + áudio
# ─────────────────────────────────────────────────────────────────────────────
def generate_lipsync(
    face_source:     str,           # caminho LOCAL ou URL pública do rosto/vídeo
    audio_source:    str,           # caminho LOCAL ou URL pública do áudio
    job_id:          str = "",
    model:           str = "kling-v1-6",
    max_retries:     int = 2,
) -> dict:
    """
    Orquestra o lip sync completo:
      1. Hospeda face_source no imgbb se for arquivo local
      2. Hospeda audio_source no imgbb se for arquivo local
      3. Cria a task de lip sync
      4. Faz polling até o resultado
      5. Baixa o vídeo resultante

    Retorna dict com:
      success       : bool
      video_url     : URL do vídeo com lip sync
      video_path    : caminho local do vídeo baixado (se disponível)
      task_id       : ID da task Kling
      error         : mensagem de erro (se falhou)
    """

    # ── Resolver URLs públicas ─────────────────────────────────────────────────
    face_url  = face_source
    audio_url = audio_source

    if face_source and os.path.exists(face_source):
        print(f"   📤 Hospedando imagem/vídeo do personagem...")
        face_url = _upload_to_imgbb(face_source, "face")
        if not face_url:
            return {"success": False, "error": "Falha ao hospedar imagem do personagem"}

    if audio_source and os.path.exists(audio_source):
        print(f"   📤 Hospedando áudio...")
        audio_url = _upload_to_imgbb(audio_source, "audio")
        if not audio_url:
            return {"success": False, "error": "Falha ao hospedar áudio"}

    if not face_url or not audio_url:
        return {"success": False, "error": "face_source e audio_source são obrigatórios"}

    # ── Tentativas com retry ───────────────────────────────────────────────────
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
            # Baixa localmente
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


# ─────────────────────────────────────────────────────────────────────────────
# DOWNLOAD DO VÍDEO RESULTANTE
# ─────────────────────────────────────────────────────────────────────────────
def _download_lipsync_video(video_url: str, job_id: str) -> Optional[str]:
    try:
        from config import UPLOAD_DIR
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
