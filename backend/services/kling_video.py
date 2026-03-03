"""
🎬 ClipVox - Kling Video Service (via PiAPI)
────────────────────────────────────────────────────────────────────
Gera clipes de vídeo usando o Kling AI via PiAPI.
Endpoint: api.piapi.ai

Auth: X-API-Key (PiAPI)
Model: kling | task_type: video_generation
"""

import os
import time
import base64
import requests
from typing import Optional

# ── PiAPI ────────────────────────────────────────────────────────────────────
PIAPI_KEY      = os.getenv("PIAPI_API_KEY", "")
PIAPI_BASE_URL = "https://api.piapi.ai/api/v1/task"

# ── imgbb (para rehosting de imagens locais) ──────────────────────────────────
IMGBB_KEY = os.getenv("IMGBB_API_KEY", "")


# ══════════════════════════════════════════════════════════════════════════════
# IMGBB REHOSTING
# ══════════════════════════════════════════════════════════════════════════════
def rehost_image_imgbb(image_path: str) -> Optional[str]:
    """
    Faz upload da imagem para imgbb para usar como frame inicial do vídeo.
    PiAPI Kling I2V aceita URL pública.
    """
    if not IMGBB_KEY:
        print("   ⚠️ IMGBB_API_KEY não configurada — tentando R2 URL")
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


# ══════════════════════════════════════════════════════════════════════════════
# CREATE KLING VIDEO TASK (via PiAPI)
# ══════════════════════════════════════════════════════════════════════════════
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
    Cria task de geração de vídeo Kling via PiAPI.
    Usa image-to-video (I2V) com a imagem da cena como frame inicial.

    Returns: task_id ou None se falhar
    """
    print(f"\n🎬 Creating video task — Scene {scene_number}")
    print(f"   Model: {model} | Mode: {mode} | {duration}s | {aspect_ratio}")

    if not PIAPI_KEY:
        print("   ❌ PIAPI_API_KEY não configurada")
        return None

    payload = {
        "model":     "kling",
        "task_type": "video_generation",
        "input": {
            "prompt":       prompt[:2500],
            "image_url":    image_url,
            "duration":     duration,
            "mode":         mode,
            "aspect_ratio": aspect_ratio,
            "model_name":   model,
        }
    }

    headers = {
        "Content-Type": "application/json",
        "X-API-Key":    PIAPI_KEY,
    }

    try:
        resp = requests.post(PIAPI_BASE_URL, headers=headers, json=payload, timeout=30)
        print(f"   📥 HTTP {resp.status_code}: {resp.text[:300]}")

        data = resp.json()
        task_id = (
            data.get("data", {}).get("task_id")
            or data.get("task_id")
        )
        if not task_id:
            print(f"   ❌ task_id não encontrado: {data}")
            return None

        print(f"   ✅ Task criada: {task_id}")
        return task_id

    except Exception as e:
        print(f"   ❌ Exceção: {e}")
        return None


# ══════════════════════════════════════════════════════════════════════════════
# POLL KLING VIDEO TASK (via PiAPI)
# ══════════════════════════════════════════════════════════════════════════════
def poll_kling_video(task_id: str, scene_number: int, timeout: int = 600) -> Optional[str]:
    """
    Aguarda conclusão da task e retorna URL do vídeo.
    Timeout padrão: 10 minutos
    """
    print(f"   ⏳ Polling task {task_id}...")

    headers = {"X-API-Key": PIAPI_KEY}

    for elapsed in range(10, timeout + 1, 10):
        time.sleep(10)
        try:
            resp = requests.get(
                f"{PIAPI_BASE_URL}/{task_id}",
                headers=headers,
                timeout=15
            )
            data = resp.json()

            status = (
                data.get("data", {}).get("status")
                or data.get("status", "")
            )
            print(f"   ⏳ Cena {scene_number} — {status} ({elapsed}s)")

            if status in ("completed", "succeed", "success"):
                output = (
                    data.get("data", {}).get("output", {})
                    or data.get("output", {})
                )
                video_url = (
                    output.get("video_url")
                    or output.get("url")
                    or (output.get("videos") or [{}])[0].get("url")
                    or (data.get("data", {}).get("videos") or [{}])[0].get("url")
                )
                if video_url:
                    print(f"   ✅ Vídeo pronto: {video_url[:80]}")
                    return video_url
                print(f"   ❌ Nenhum vídeo no resultado: {data}")
                return None

            elif status in ("failed", "error"):
                error_msg = (
                    data.get("data", {}).get("error", {}).get("message", "")
                    or str(data.get("error", ""))
                )
                print(f"   ❌ Task falhou: {error_msg}")
                return None

        except Exception as e:
            print(f"   ⚠️ Polling erro: {e}")

    print(f"   ❌ Timeout ({timeout}s) — Cena {scene_number}")
    return None


# ══════════════════════════════════════════════════════════════════════════════
# GENERATE SINGLE CLIP (imagem → vídeo)
# ══════════════════════════════════════════════════════════════════════════════
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
    Usa Kling via PiAPI (I2V).

    Returns dict com: success, video_url, video_path, scene_number, task_id
    """

    # ── Garantir URL pública da imagem ────────────────────────────────────────
    public_url = image_url

    # Se a URL for local ou inválida, tenta imgbb
    if not public_url or public_url.startswith("/api/") or public_url.startswith("/"):
        print(f"   📤 URL local detectada — fazendo upload imgbb...")
        public_url = rehost_image_imgbb(image_path)
        if not public_url and image_path and os.path.exists(image_path):
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


# ══════════════════════════════════════════════════════════════════════════════
# DOWNLOAD VIDEO
# ══════════════════════════════════════════════════════════════════════════════
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


# ══════════════════════════════════════════════════════════════════════════════
# GENERATE CLIPS BATCH
# ══════════════════════════════════════════════════════════════════════════════
def generate_video_clips_batch(
    scenes: list,
    aspect_ratio: str = "16:9",
    duration: int = 5,
    mode: str = "std",
    model: str = "kling-v1-6",
    job_id: str = ""
) -> list:
    """
    Gera clipes de vídeo para múltiplas cenas em batch via Kling (PiAPI).

    scenes: lista de dicts com {scene_number, prompt, image_path, image_url}
    Returns: lista de resultados por cena
    """
    results          = []
    successful_count = 0

    print(f"\n🎬 Generating {len(scenes)} video clips via Kling (PiAPI)...")
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


# ══════════════════════════════════════════════════════════════════════════════
# ALIAS para compatibilidade com videos.py existente
# ══════════════════════════════════════════════════════════════════════════════
generate_videos_batch = generate_video_clips_batch
