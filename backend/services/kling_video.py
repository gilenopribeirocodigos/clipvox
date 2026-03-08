"""
🎬 ClipVox - Kling Video Service (via PiAPI)
Gera clipes de vídeo usando PiAPI como intermediário do Kling AI.
Auth: x-api-key (PIAPI_API_KEY)
"""

import os
import time
import base64
import requests
from typing import Optional

PIAPI_API_KEY = os.getenv("PIAPI_API_KEY", "")
PIAPI_BASE    = "https://api.piapi.ai"
IMGBB_KEY     = os.getenv("IMGBB_API_KEY", "")


def _auth_headers() -> dict:
    if not PIAPI_API_KEY:
        raise ValueError("PIAPI_API_KEY não configurada")
    return {
        "Content-Type": "application/json",
        "x-api-key":    PIAPI_API_KEY,
    }


def rehost_image_imgbb(image_path: str) -> Optional[str]:
    if not IMGBB_KEY:
        print("   IMGBB_API_KEY nao configurada")
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
                time.sleep(3)
                print(f"   imgbb OK: {url}")
                return url
        print(f"   imgbb falhou: HTTP {resp.status_code}")
        return None
    except Exception as e:
        print(f"   imgbb erro: {e}")
        return None


def _image_to_base64(image_path: str) -> str:
    with open(image_path, "rb") as f:
        return base64.b64encode(f.read()).decode("utf-8")


def create_kling_video_task(
    image_url: str,
    prompt: str,
    scene_number: int,
    aspect_ratio: str = "16:9",
    duration: int = 5,
    mode: str = "std",
    model: str = "kling"
) -> Optional[str]:
    print(f"\nCreating video task Scene {scene_number} | {model} | {mode} | {duration}s")

    if not PIAPI_API_KEY:
        print("   PIAPI_API_KEY nao configurada")
        return None

    # PiAPI: endpoint único /api/v1/task com task_type "video_generation"
    payload = {
        "model":     model,
        "task_type": "video_generation",
        "input": {
            "prompt":       prompt[:2500],
            "image_url":    image_url,
            "duration":     duration,
            "mode":         mode,
            "aspect_ratio": aspect_ratio,
        }
    }

    try:
        resp = requests.post(
            f"{PIAPI_BASE}/api/v1/task",
            headers=_auth_headers(),
            json=payload,
            timeout=30
        )
        print(f"   HTTP {resp.status_code}: {resp.text[:300]}")
        data = resp.json()

        # PiAPI retorna code 200 em sucesso
        if data.get("code") != 200:
            print(f"   Erro PiAPI: {data.get('message')}")
            return None

        task_id = data.get("data", {}).get("task_id")
        print(f"   Task criada: {task_id}")
        return task_id
    except Exception as e:
        print(f"   Excecao: {e}")
        return None


def poll_kling_video(task_id: str, scene_number: int, timeout: int = 600) -> Optional[str]:
    print(f"   Polling task {task_id}...")

    for elapsed in range(10, timeout + 1, 10):
        time.sleep(10)
        try:
            resp = requests.get(
                f"{PIAPI_BASE}/api/v1/task/{task_id}",
                headers=_auth_headers(),
                timeout=15
            )
            data   = resp.json()
            task   = data.get("data", {})
            # PiAPI usa "status": pending | processing | completed | failed
            status = task.get("status", "")
            print(f"   Cena {scene_number} - {status} ({elapsed}s)")

            if status == "completed":
                # URL em: data.output.works[0].video.resource
                works = task.get("output", {}).get("works", [])
                if works:
                    video_url = works[0].get("video", {}).get("resource")
                    if video_url:
                        print(f"   Video pronto: {video_url[:80]}")
                        return video_url
                print(f"   Nenhum video no resultado")
                return None

            elif status == "failed":
                error = task.get("error", {}).get("message", "desconhecido")
                print(f"   Task falhou: {error}")
                return None

        except Exception as e:
            print(f"   Polling erro: {e}")

    print(f"   Timeout ({timeout}s) Cena {scene_number}")
    return None


def _upload_video_to_r2(video_path: str, scene_number: int, job_id: str) -> Optional[str]:
    """Faz upload do vídeo para Cloudflare R2 para persistência."""
    try:
        import boto3
        R2_ACCESS_KEY = os.getenv("R2_ACCESS_KEY_ID", "")
        R2_SECRET_KEY = os.getenv("R2_SECRET_ACCESS_KEY", "")
        R2_ENDPOINT   = os.getenv("R2_ENDPOINT_URL", "")
        R2_BUCKET     = os.getenv("R2_BUCKET_NAME", "clipvox-images")
        R2_PUBLIC_URL = os.getenv("R2_PUBLIC_URL", "").rstrip("/")

        if not all([R2_ACCESS_KEY, R2_SECRET_KEY, R2_ENDPOINT, R2_PUBLIC_URL]):
            print("   ⚠️ R2 não configurado — vídeo salvo apenas localmente")
            return None

        r2 = boto3.client(
            "s3",
            endpoint_url=R2_ENDPOINT,
            aws_access_key_id=R2_ACCESS_KEY,
            aws_secret_access_key=R2_SECRET_KEY,
        )
        filename = f"clip_{scene_number:03d}.mp4"
        r2_key   = f"jobs/{job_id}/{filename}"
        with open(video_path, "rb") as f:
            r2.put_object(Bucket=R2_BUCKET, Key=r2_key, Body=f, ContentType="video/mp4")
        r2_url = f"{R2_PUBLIC_URL}/{r2_key}"
        print(f"   ✅ Video no R2: {r2_url}")
        return r2_url
    except Exception as e:
        print(f"   ⚠️ Erro upload R2: {e}")
        return None


def _download_video(video_url: str, scene_number: int, job_id: str) -> tuple:
    """Baixa o vídeo, faz upload para R2. Retorna (local_path, r2_url)."""
    try:
        from config import UPLOAD_DIR
        resp = requests.get(video_url, timeout=120, stream=True)
        if resp.status_code != 200:
            return None, None
        filename   = f"clip_{scene_number:03d}.mp4"
        local_path = os.path.join(UPLOAD_DIR, f"job_{job_id}_{filename}" if job_id else filename)
        with open(local_path, "wb") as f:
            for chunk in resp.iter_content(chunk_size=8192):
                f.write(chunk)
        print(f"   Video salvo: {local_path}")

        r2_url = _upload_video_to_r2(local_path, scene_number, job_id)
        return local_path, r2_url
    except Exception as e:
        print(f"   Erro ao baixar video: {e}")
        return None, None


def generate_video_clip(
    image_path: str,
    image_url: str,
    prompt: str,
    scene_number: int,
    aspect_ratio: str = "16:9",
    duration: int = 5,
    mode: str = "std",
    model: str = "kling",
    job_id: str = "",
    max_retries: int = 3
) -> dict:
    public_url = image_url

    if not public_url or public_url.startswith("/api/") or public_url.startswith("/"):
        print(f"   URL local - fazendo upload imgbb...")
        public_url = rehost_image_imgbb(image_path)
        if not public_url and image_path and os.path.exists(image_path):
            public_url = f"data:image/jpeg;base64,{_image_to_base64(image_path)}"

    for attempt in range(1, max_retries + 1):
        print(f"\nScene {scene_number} Attempt {attempt}/{max_retries}")

        task_id = create_kling_video_task(
            image_url=public_url, prompt=prompt, scene_number=scene_number,
            aspect_ratio=aspect_ratio, duration=duration, mode=mode, model=model
        )

        if not task_id:
            time.sleep(15 * attempt)
            continue

        video_url = poll_kling_video(task_id, scene_number)

        if video_url:
            local_path, r2_url = _download_video(video_url, scene_number, job_id)
            final_url = r2_url or video_url
            return {
                "success":      True,
                "scene_number": scene_number,
                "video_url":    final_url,
                "video_path":   local_path,
                "task_id":      task_id,
                "attempt":      attempt,
            }

        time.sleep(20 * attempt)

    return {
        "success":      False,
        "scene_number": scene_number,
        "video_url":    None,
        "video_path":   None,
        "task_id":      None,
        "error":        f"Falhou apos {max_retries} tentativas",
    }


def generate_video_clips_batch(
    scenes: list,
    aspect_ratio: str = "16:9",
    duration: int = 5,
    mode: str = "std",
    model: str = "kling",
    job_id: str = "",
    bpm: int = None,
    **kwargs
) -> list:
    results = []
    successful_count = 0
    print(f"\nGenerating {len(scenes)} video clips via PiAPI (Kling)...")
    print(f"   Model: {model} | Mode: {mode} | {duration}s | {aspect_ratio}")

    for scene in scenes:
        result = generate_video_clip(
            image_path=scene.get("image_path", ""),
            image_url=scene.get("image_url", ""),
            prompt=scene.get("prompt", ""),
            scene_number=scene["scene_number"],
            aspect_ratio=aspect_ratio,
            duration=duration, mode=mode, model=model, job_id=job_id
        )
        if result["success"]:
            successful_count += 1
        results.append(result)
        if scene != scenes[-1]:
            time.sleep(5)

    print(f"\nGenerated {successful_count}/{len(scenes)} clips successfully")
    return results


# Alias para compatibilidade com videos.py existente
generate_videos_batch = generate_video_clips_batch
