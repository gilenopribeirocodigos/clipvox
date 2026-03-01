"""
🎬 ClipVox - Kling Video Generation Service (via PiAPI)
Payload simplificado — apenas campos obrigatórios confirmados pela PiAPI
"""

import os
import time
import requests
from typing import Optional

PIAPI_KEY        = os.getenv("PIAPI_API_KEY") or os.getenv("PIAPI_KEY")
PIAPI_BASE       = "https://api.piapi.ai/api/v1/task"
MAX_WAIT_SECONDS = 300
POLL_INTERVAL    = 5


def get_clip_duration_from_bpm(bpm: float) -> int:
    return 5  # Kling aceita 5 ou 10


def generate_scene_video(
    image_url: str,
    prompt: str,
    scene_number: int,
    bpm: float = 120,
    aspect_ratio: str = "16:9",
    mode: str = "std"
) -> dict:

    if not PIAPI_KEY:
        return _video_error(scene_number, "PIAPI_API_KEY not configured")

    if not image_url:
        return _video_error(scene_number, "No image URL provided")

    duration      = get_clip_duration_from_bpm(bpm)
    motion_prompt = _build_motion_prompt(prompt, scene_number)

    print(f"\n🎬 Gerando vídeo — Cena {scene_number}")
    print(f"   image_url: {image_url}")
    print(f"   duration: {duration}s | mode: {mode} | aspect_ratio: {aspect_ratio}")

    headers = {
        "x-api-key":    PIAPI_KEY,
        "Content-Type": "application/json"
    }

    # ✅ Payload MÍNIMO — só campos confirmados pela PiAPI para Kling image-to-video
    payload = {
        "model":     "kling",
        "task_type": "video_generation",
        "input": {
            "prompt":       motion_prompt,
            "image_url":    image_url,
            "duration":     duration,
            "aspect_ratio": aspect_ratio,
            "mode":         mode
        }
    }

    print(f"   📤 Payload: {payload}")

    try:
        response = requests.post(
            PIAPI_BASE,
            headers=headers,
            json=payload,
            timeout=30
        )

        print(f"   📥 HTTP {response.status_code}: {response.text[:500]}")

        if response.status_code not in (200, 201):
            try:
                err_body = response.json()
                err_msg  = err_body.get("message") or err_body.get("error") or str(err_body)
            except Exception:
                err_msg = response.text[:300]
            print(f"❌ PiAPI HTTP {response.status_code}: {err_msg}")
            return _video_error(scene_number, f"HTTP {response.status_code}: {err_msg[:120]}")

        data = response.json()
        print(f"   📥 Resposta completa: {data}")

        # ─── Checar se a task já falhou na criação ────────────
        task_data = data.get("data", data)
        if task_data.get("status") in ("failed", "error"):
            err = task_data.get("error", {})
            err_msg = err.get("message") if isinstance(err, dict) else str(err)
            print(f"❌ Task falhou na criação: {err_msg}")
            print(f"   Detalhes completos: {task_data}")
            return _video_error(scene_number, f"Task failed on creation: {err_msg}")

        task_id = (
            task_data.get("task_id") or
            data.get("task_id") or
            data.get("id")
        )

        if not task_id:
            print(f"❌ task_id não encontrado: {data}")
            return _video_error(scene_number, "No task_id in response")

        print(f"   ✅ Task criada: {task_id}")

        video_url = _poll_task(task_id, scene_number)

        if video_url:
            print(f"   ✅ Vídeo gerado: {video_url}")
            return {
                "success":      True,
                "scene_number": scene_number,
                "task_id":      task_id,
                "video_url":    video_url,
                "duration":     duration,
                "mode":         mode,
                "aspect_ratio": aspect_ratio
            }
        else:
            return _video_error(scene_number, "Timeout waiting for video")

    except requests.exceptions.Timeout:
        return _video_error(scene_number, "Request timeout")
    except Exception as e:
        print(f"❌ Exceção: {e}")
        import traceback; traceback.print_exc()
        return _video_error(scene_number, str(e))


def _poll_task(task_id: str, scene_number: int) -> Optional[str]:
    headers = {
        "x-api-key":    PIAPI_KEY,
        "Content-Type": "application/json"
    }

    elapsed = 0
    while elapsed < MAX_WAIT_SECONDS:
        time.sleep(POLL_INTERVAL)
        elapsed += POLL_INTERVAL

        try:
            response = requests.get(f"{PIAPI_BASE}/{task_id}", headers=headers, timeout=15)

            if response.status_code != 200:
                print(f"   ⚠️ Polling HTTP {response.status_code}")
                continue

            data      = response.json()
            task_data = data.get("data", data)
            status    = task_data.get("status", "")

            print(f"   ⏳ Cena {scene_number} status: {status} ({elapsed}s)")

            if status in ("completed", "succeed", "success", 99):
                return _extract_video_url(task_data)

            elif status in ("failed", "error", "cancelled"):
                err = task_data.get("error", {})
                print(f"   ❌ Task falhou no polling: {err}")
                print(f"   Dados completos: {task_data}")
                return None

        except Exception as e:
            print(f"   ⚠️ Polling erro: {e}")

    print(f"   ⏱️ Timeout {MAX_WAIT_SECONDS}s")
    return None


def _extract_video_url(task_data: dict) -> Optional[str]:
    output = task_data.get("output", {})
    works  = output.get("works", [])

    if works:
        video = works[0].get("video", {})
        url = video.get("resource_without_watermark") or video.get("resource")
        if url:
            return url

    return (
        output.get("video_url") or
        output.get("url") or
        task_data.get("video_url") or
        task_data.get("url")
    )


def generate_videos_batch(scenes, bpm=120, aspect_ratio="16:9", mode="std"):
    results       = []
    success_count = 0
    total         = len(scenes)

    print(f"\n🎬 Gerando {total} vídeos — Kling AI (PiAPI) | modo: {mode}")

    for i, scene in enumerate(scenes):
        scene_number = scene.get("scene_number", i + 1)
        image_url    = scene.get("image_url") or scene.get("r2_url")
        prompt       = scene.get("prompt", "")

        print(f"\n[{i+1}/{total}] Cena {scene_number}...")
        result = generate_scene_video(
            image_url=image_url, prompt=prompt,
            scene_number=scene_number, bpm=bpm,
            aspect_ratio=aspect_ratio, mode=mode
        )

        if result["success"]:
            success_count += 1
        results.append(result)

    print(f"\n✅ Concluído: {success_count}/{total}")
    return results


def _build_motion_prompt(scene_prompt: str, scene_number: int) -> str:
    scene_lower = scene_prompt.lower()
    if any(w in scene_lower for w in ["action", "fight", "run", "energy"]):
        motion = "dynamic camera movement, fast pan"
    elif any(w in scene_lower for w in ["calm", "slow", "peaceful", "night"]):
        motion = "slow gentle pan, smooth cinematic movement"
    elif any(w in scene_lower for w in ["landscape", "nature", "sky"]):
        motion = "slow dolly forward, cinematic wide shot"
    elif any(w in scene_lower for w in ["face", "portrait", "close"]):
        motion = "subtle zoom in, gentle rack focus"
    else:
        motion = "smooth cinematic pan, subtle camera movement"
    return f"{scene_prompt[:300]}, {motion}"[:500]


def _video_error(scene_number, message):
    return {"success": False, "scene_number": scene_number,
            "task_id": None, "video_url": None, "duration": 5, "error": message}
