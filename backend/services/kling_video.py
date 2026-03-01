"""
🎬 ClipVox - Kling Video Generation Service (via PiAPI)
Solução para rate-limit do R2: rehosting de imagens via imgbb antes de enviar ao Kling
"""

import os
import time
import requests
import base64
from typing import Optional

PIAPI_KEY        = os.getenv("PIAPI_API_KEY") or os.getenv("PIAPI_KEY")
IMGBB_API_KEY    = os.getenv("IMGBB_API_KEY", "")
PIAPI_BASE       = "https://api.piapi.ai/api/v1/task"
MAX_WAIT_SECONDS = 300
POLL_INTERVAL    = 5


# ═══════════════════════════════════════════════════════════════
# STEP 0: Baixar imagem do R2 e fazer rehost via imgbb
# ═══════════════════════════════════════════════════════════════
def rehost_image_imgbb(image_url: str, scene_number: int) -> Optional[str]:
    """
    Baixa a imagem do R2/Workers e faz upload para imgbb.
    Retorna a URL pública do imgbb (aceita pelo Kling) ou None se falhar.
    """
    print(f"   📥 Baixando imagem: {image_url[:80]}")

    try:
        r = requests.get(image_url, timeout=30)
        if r.status_code != 200:
            print(f"   ❌ Falha ao baixar imagem (HTTP {r.status_code})")
            return None

        image_bytes = r.content
        image_b64   = base64.b64encode(image_bytes).decode("utf-8")
        print(f"   ✅ Imagem baixada ({len(image_bytes)//1024}KB)")

        if not IMGBB_API_KEY:
            print(f"   ❌ IMGBB_API_KEY não configurada")
            return None

        upload_url = f"https://api.imgbb.com/1/upload?key={IMGBB_API_KEY}"
        resp = requests.post(
            upload_url,
            data={"image": image_b64, "name": f"clipvox_scene_{scene_number}"},
            timeout=60
        )

        print(f"   📥 imgbb response HTTP {resp.status_code}: {resp.text[:200]}")

        if resp.status_code != 200:
            print(f"   ❌ imgbb upload falhou")
            return None

        data = resp.json()
        imgbb_url = data.get("data", {}).get("url")

        if imgbb_url:
            print(f"   ✅ imgbb URL: {imgbb_url}")
            return imgbb_url
        else:
            print(f"   ❌ URL não encontrada na resposta imgbb")
            return None

    except Exception as e:
        print(f"   ⚠️ Erro no rehost: {e}")
        return None


# ═══════════════════════════════════════════════════════════════
# GERAR VÍDEO DE UMA CENA
# ═══════════════════════════════════════════════════════════════
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

    duration = 5

    print(f"\n🎬 Gerando vídeo — Cena {scene_number}")
    print(f"   duration: {duration}s | mode: {mode} | aspect_ratio: {aspect_ratio}")

    imgbb_url = rehost_image_imgbb(image_url, scene_number)

    if not imgbb_url:
        print(f"   ❌ Rehost falhou — abortando cena {scene_number}")
        return _video_error(scene_number, "Falha no rehost via imgbb")

    print(f"   🔗 URL enviada para Kling: {imgbb_url}")

    motion_prompt = _build_motion_prompt(prompt, scene_number)

    headers = {
        "x-api-key":    PIAPI_KEY,
        "Content-Type": "application/json"
    }

    payload = {
        "model":     "kling",
        "task_type": "video_generation",
        "input": {
            "prompt":       motion_prompt,
            "image_url":    imgbb_url,
            "duration":     duration,
            "aspect_ratio": aspect_ratio,
            "mode":         mode
        }
    }

    try:
        response = requests.post(PIAPI_BASE, headers=headers, json=payload, timeout=30)

        print(f"   📥 HTTP {response.status_code}: {response.text[:500]}")

        if response.status_code not in (200, 201):
            try:
                err_body = response.json()
                err_msg  = err_body.get("message") or str(err_body)
            except Exception:
                err_msg = response.text[:300]
            print(f"❌ PiAPI HTTP {response.status_code}: {err_msg}")
            return _video_error(scene_number, f"HTTP {response.status_code}: {err_msg[:120]}")

        data      = response.json()
        task_data = data.get("data", data)

        if task_data.get("status") in ("failed", "error"):
            err     = task_data.get("error", {})
            err_msg = err.get("message") if isinstance(err, dict) else str(err)
            print(f"❌ Task falhou na criação: {err_msg}")
            return _video_error(scene_number, f"Task failed: {err_msg}")

        task_id = task_data.get("task_id") or data.get("task_id") or data.get("id")

        if not task_id:
            print(f"❌ task_id não encontrado: {data}")
            return _video_error(scene_number, "No task_id in response")

        print(f"   ✅ Task criada: {task_id}")

        video_url = _poll_task(task_id, scene_number)

        if video_url:
            print(f"   ✅ Vídeo pronto: {video_url[:80]}")
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
            return _video_error(scene_number, "Timeout or failed during polling")

    except requests.exceptions.Timeout:
        return _video_error(scene_number, "Request timeout")
    except Exception as e:
        print(f"❌ Exceção: {e}")
        import traceback; traceback.print_exc()
        return _video_error(scene_number, str(e))


# ═══════════════════════════════════════════════════════════════
# POLLING
# ═══════════════════════════════════════════════════════════════
def _poll_task(task_id: str, scene_number: int) -> Optional[str]:
    headers = {"x-api-key": PIAPI_KEY, "Content-Type": "application/json"}
    elapsed = 0

    while elapsed < MAX_WAIT_SECONDS:
        time.sleep(POLL_INTERVAL)
        elapsed += POLL_INTERVAL

        try:
            r         = requests.get(f"{PIAPI_BASE}/{task_id}", headers=headers, timeout=15)
            data      = r.json()
            task_data = data.get("data", data)
            status    = task_data.get("status", "")

            print(f"   ⏳ Cena {scene_number} — status: {status} ({elapsed}s)")

            if status in ("completed", "succeed", "success", 99):
                return _extract_video_url(task_data)

            elif status in ("failed", "error", "cancelled"):
                err = task_data.get("error", {})
                print(f"   ❌ Falhou no polling: {err}")
                return None

        except Exception as e:
            print(f"   ⚠️ Polling erro: {e}")

    return None


def _extract_video_url(task_data: dict) -> Optional[str]:
    output = task_data.get("output", {})
    works  = output.get("works", [])
    if works:
        video = works[0].get("video", {})
        url   = video.get("resource_without_watermark") or video.get("resource")
        if url:
            return url
    return (
        output.get("video_url") or output.get("url") or
        task_data.get("video_url") or task_data.get("url")
    )


# ═══════════════════════════════════════════════════════════════
# BATCH
# ═══════════════════════════════════════════════════════════════
def generate_videos_batch(scenes, bpm=120, aspect_ratio="16:9", mode="std"):
    results       = []
    success_count = 0
    total         = len(scenes)

    print(f"\n🎬 Gerando {total} vídeos — Kling AI via PiAPI | modo: {mode}")

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

    print(f"\n✅ Concluído: {success_count}/{total} vídeos gerados")
    return results


# ═══════════════════════════════════════════════════════════════
# HELPERS
# ═══════════════════════════════════════════════════════════════
def _build_motion_prompt(scene_prompt: str, scene_number: int) -> str:
    s = scene_prompt.lower()
    if any(w in s for w in ["action", "fight", "run", "energy"]):
        motion = "dynamic camera movement, fast pan"
    elif any(w in s for w in ["calm", "slow", "peaceful", "night"]):
        motion = "slow gentle pan, smooth cinematic movement"
    elif any(w in s for w in ["landscape", "nature", "sky"]):
        motion = "slow dolly forward, cinematic wide shot"
    elif any(w in s for w in ["face", "portrait", "close"]):
        motion = "subtle zoom in, gentle rack focus"
    else:
        motion = "smooth cinematic pan, subtle camera movement"
    return f"{scene_prompt[:300]}, {motion}"[:500]


def _video_error(scene_number, message):
    return {"success": False, "scene_number": scene_number,
            "task_id": None, "video_url": None, "duration": 5, "error": message}

def get_clip_duration_from_bpm(bpm):
    return 5
