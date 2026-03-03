"""
🎬 ClipVox - Kling Video Service (API Oficial - sem PiAPI!)
──────────────────────────────────────────────────────────
Gera clipes de vídeo usando a API oficial do Kling AI
Endpoint: api.klingai.com

Auth: JWT com Access Key + Secret Key
"""

import os
import time
import base64
import requests
import jwt
from typing import Optional

# ── Kling API Oficial ─────────────────────────────────────────────
KLING_ACCESS_KEY = os.getenv("KLING_ACCESS_KEY", "")
KLING_SECRET_KEY = os.getenv("KLING_SECRET_KEY", "")
KLING_API_BASE   = "https://api.klingai.com"


# ═══════════════════════════════════════════════════════════════
# JWT AUTHENTICATION
# ═══════════════════════════════════════════════════════════════
def _get_jwt_token() -> str:
    """Gera JWT token para autenticação na API oficial do Kling."""
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
        "Content-Type": "application/json",
        "Authorization": f"Bearer {_get_jwt_token()}"
    }


# ═══════════════════════════════════════════════════════════════
# IMGBB (mantido para compatibilidade — hospedar imagem para I2V)
# ═══════════════════════════════════════════════════════════════
IMGBB_KEY = os.getenv("IMGBB_API_KEY", "")

def rehost_image_imgbb(image_path: str) -> Optional[str]:
    """
    Faz upload da imagem para imgbb para usar como frame inicial do vídeo.
    A API oficial do Kling para I2V aceita URL pública (não base64 direto).
    """
    if not IMGBB_KEY:
        print("   ⚠️ IMGBB_API_KEY não configurada — tentando base64")
        return None
    try:
        with open(image_path, "rb") as f:
            b64 = base64.b64encode(f.read()).decode("utf-8")
        resp = requests.post(
            f"https://api.imgbb.com/1/upload?key={IMGBB_KEY}",
            data={"image": b64, "name": f"clipvox_{int(time.time())}"},
            timeout=60
        )
        if resp.status_code == 200:
            url = resp.json().get("data", {}).get("url")
            if url:
                time.sleep(3)  # CDN propagation
                print(f"   ✅ imgbb: {url}")
                return url
        print(f"   ❌ imgbb falhou: HTTP {resp.status_code}")
        return None
    except Exception as e:
        print(f"   ❌ imgbb erro: {e}")
        return None


def _image_to_base64(image_path: str) -> str:
    with open(image_path, "rb") as f:
        return base64.b64encode(f.read()).decode("utf-8")


# ═══════════════════════════════════════════════════════════════
# CREATE KLING VIDEO TASK (API OFICIAL)
# ═══════════════════════════════════════════════════════════════
def create_kling_video_task(
    image_url: str,
    prompt: str,
    scene_number: int,
    aspect_ratio: str = "16:9",
    duration: int = 5,
    mode: str = "std",
    model: str = "kling-v1-6"
) -> Optional[str]:
    """
    Cria task de geração de vídeo via API oficial do Kling.
    Usa image-to-video (I2V) com a imagem da cena como frame inicial.

    Returns: task_id ou None se falhar
    """
    print(f"\n🎬 Creating video task — Scene {scene_number}")
    print(f"   Model: {model} | Mode: {mode} | {duration}s | {aspect_ratio}")

    payload = {
        "model_name":     model,
        "prompt":         prompt[:2500],
        "image":          image_url,   # URL pública da imagem
        "duration":       str(duration),
        "mode":           mode,
        "aspect_ratio":   aspect_ratio,
    }

    try:
        resp = requests.post(
            f"{KLING_API_BASE}/v1/videos/image2video",
            headers=_auth_headers(),
            json=payload,
            timeout=30
        )
        print(f"   📥 HTTP {resp.status_code}: {resp.text[:300]}")

        data = resp.json()
        if data.get("code") != 0:
            print(f"   ❌ Erro: {data.get('message')}")
            return None

        task_id = data.get("data", {}).get("task_id")
        print(f"   ✅ Task criada: {task_id}")
        return task_id

    except Exception as e:
        print(f"   ❌ Exceção: {e}")
        return None


# ═══════════════════════════════════════════════════════════════
# POLL KLING VIDEO TASK
# ═══════════════════════════════════════════════════════════════
def poll_kling_video(task_id: str, scene_number: int, timeout: int = 600) -> Optional[str]:
    """
    Aguarda conclusão da task e retorna URL do vídeo.
    Timeout padrão: 10 minutos
    """
    print(f"   ⏳ Polling task {task_id}...")

    for elapsed in range(10, timeout + 1, 10):
        time.sleep(10)
        try:
            resp = requests.get(
                f"{KLING_API_BASE}/v1/videos/image2video/{task_id}",
                headers=_auth_headers(),
                timeout=15
            )
            data = resp.json()

            if data.get("code") != 0:
                print(f"   ❌ Polling erro: {data.get('message')}")
                return None

            task_info = data.get("data", {})
            status    = task_info.get("task_status", "")
            print(f"   ⏳ Cena {scene_number} — {status} ({elapsed}s)")

            if status == "succeed":
                videos = task_info.get("task_result", {}).get("videos", [])
                if videos:
                    video_url = videos[0].get("url")
                    print(f"   ✅ Vídeo pronto: {video_url[:80]}")
                    return video_url
                print(f"   ❌ Nenhum vídeo no resultado: {task_info}")
                return None

            elif status == "failed":
                print(f"   ❌ Task falhou: {task_info.get('task_status_msg')}")
                return None

        except Exception as e:
            print(f"   ⚠️ Polling erro: {e}")

    print(f"   ❌ Timeout ({timeout}s) — Cena {scene_number}")
    return None


# ═══════════════════════════════════════════════════════════════
# GENERATE SINGLE CLIP (imagem → vídeo)
# ═══════════════════════════════════════════════════════════════
def generate_video_clip(
    image_path: str,
    image_url: str,
    prompt: str,
    scene_number: int,
    aspect_ratio: str = "16:9",
    duration: int = 5,
    mode: str = "std",
    model: str = "kling-v1-6",
    job_id: str = "",
    max_retries: int = 3
) -> dict:
    """
    Gera um clipe de vídeo a partir de uma imagem de cena.
    Usa a API oficial do Kling (sem PiAPI).

    Returns dict com: success, video_url, video_path, scene_number, task_id
    """

    # ── Garantir URL pública da imagem ────────────────────────
    # A API I2V do Kling precisa de URL pública, não base64
    public_url = image_url

    # Se a URL for local ou inválida, tenta imgbb
    if not public_url or public_url.startswith("/api/"):
        print(f"   📤 URL local detectada — fazendo upload imgbb...")
        public_url = rehost_image_imgbb(image_path)
        if not public_url:
            # Fallback: tenta usar base64 diretamente
            print(f"   📤 Tentando base64 como fallback...")
            public_url = f"data:image/jpeg;base64,{_image_to_base64(image_path)}"

    for attempt in range(1, max_retries + 1):
        print(f"\n🎬 Scene {scene_number} — Attempt {attempt}/{max_retries}")

        task_id = create_kling_video_task(
            image_url=public_url,
            prompt=prompt,
            scene_number=scene_number,
            aspect_ratio=aspect_ratio,
            duration=duration,
            mode=mode,
            model=model
        )

        if not task_id:
            print(f"   ⚠️ Falha ao criar task — aguardando antes de retry...")
            time.sleep(15 * attempt)
            continue

        video_url = poll_kling_video(task_id, scene_number)

        if video_url:
            # Baixar vídeo localmente
            local_path = _download_video(video_url, scene_number, job_id)
            return {
                "success":      True,
                "scene_number": scene_number,
                "video_url":    video_url,
                "video_path":   local_path,
                "task_id":      task_id,
                "attempt":      attempt,
            }

        print(f"   ⚠️ Vídeo não gerado — aguardando retry...")
        time.sleep(20 * attempt)

    print(f"   ❌ Scene {scene_number} falhou após {max_retries} tentativas")
    return {
        "success":      False,
        "scene_number": scene_number,
        "video_url":    None,
        "video_path":   None,
        "task_id":      None,
        "error":        f"Falhou após {max_retries} tentativas",
    }


# ═══════════════════════════════════════════════════════════════
# DOWNLOAD VIDEO
# ═══════════════════════════════════════════════════════════════
def _download_video(video_url: str, scene_number: int, job_id: str) -> Optional[str]:
    """Baixa o vídeo gerado para armazenamento local temporário."""
    try:
        from config import UPLOAD_DIR
        resp = requests.get(video_url, timeout=120, stream=True)
        if resp.status_code != 200:
            return None

        filename   = f"clip_{scene_number:03d}.mp4"
        local_path = os.path.join(UPLOAD_DIR, f"job_{job_id}_{filename}" if job_id else filename)

        with open(local_path, "wb") as f:
            for chunk in resp.iter_content(chunk_size=8192):
                f.write(chunk)

        print(f"   💾 Vídeo salvo: {local_path}")
        return local_path
    except Exception as e:
        print(f"   ❌ Erro ao baixar vídeo: {e}")
        return None


# ═══════════════════════════════════════════════════════════════
# GENERATE CLIPS BATCH
# ═══════════════════════════════════════════════════════════════
def generate_video_clips_batch(
    scenes: list,
    aspect_ratio: str = "16:9",
    duration: int = 5,
    mode: str = "std",
    model: str = "kling-v1-6",
    job_id: str = ""
) -> list:
    """
    Gera clipes de vídeo para múltiplas cenas em batch.

    scenes: lista de dicts com {scene_number, prompt, image_path, image_url}
    Returns: lista de resultados por cena
    """
    results         = []
    successful_count = 0

    print(f"\n🎬 Generating {len(scenes)} video clips via Kling API Oficial...")
    print(f"   Model:        {model}")
    print(f"   Mode:         {mode}")
    print(f"   Duration:     {duration}s")
    print(f"   Aspect Ratio: {aspect_ratio}")

    for scene in scenes:
        result = generate_video_clip(
            image_path=scene.get("image_path", ""),
            image_url=scene.get("image_url", ""),
            prompt=scene.get("prompt", ""),
            scene_number=scene["scene_number"],
            aspect_ratio=aspect_ratio,
            duration=duration,
            mode=mode,
            model=model,
            job_id=job_id
        )

        if result["success"]:
            successful_count += 1
        results.append(result)

        # Delay entre cenas para evitar rate limit
        if scene != scenes[-1]:
            time.sleep(5)

    print(f"\n✅ Generated {successful_count}/{len(scenes)} clips successfully")
    return results
