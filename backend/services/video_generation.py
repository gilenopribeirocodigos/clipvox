"""
🎬 ClipVox - Video Generation Service (Nano Banana 2 via fal.ai)
────────────────────────────────────────────────────────────────────
Sem referência  → fal-ai/nano-banana-2 (text-to-image)
Com referência  → fal-ai/nano-banana-2/edit (consistency / image editing)
Mantém a interface atual do backend para não quebrar o restante do sistema.
"""

import mimetypes
import os
import time
from typing import Optional, List, Dict, Any
from urllib.parse import urlparse

import requests
from PIL import Image

from config import (
    FAL_KEY,
    FAL_NANO_BANANA_MODEL,
    FAL_NANO_BANANA_EDIT_MODEL,
    FAL_REQUEST_TIMEOUT_SECONDS,
    FAL_POLL_INTERVAL_SECONDS,
    UPLOAD_DIR,
    VISUAL_STYLES,
    R2_BUCKET_NAME,
    R2_PUBLIC_URL,
    get_r2_client,
)

try:
    import fal_client
except Exception:  # pragma: no cover
    fal_client = None

jobs_cache: dict = {}


def set_jobs_cache(db: dict):
    global jobs_cache
    jobs_cache = db


def _require_fal() -> None:
    if not FAL_KEY:
        raise RuntimeError("FAL_KEY não configurada")
    if fal_client is None:
        raise RuntimeError("fal-client não instalado. Adicione fal-client ao requirements.txt")


def _fal_unwrap(result: Any) -> Dict[str, Any]:
    if isinstance(result, dict) and isinstance(result.get("data"), dict):
        return result["data"]
    return result if isinstance(result, dict) else {}


def _fal_submit_and_wait(endpoint: str, arguments: Dict[str, Any], timeout_s: int = FAL_REQUEST_TIMEOUT_SECONDS) -> Dict[str, Any]:
    _require_fal()
    start = time.time()
    handler = fal_client.submit(endpoint, arguments=arguments)
    request_id = getattr(handler, "request_id", "")
    print(f"   ✅ fal task criada: {request_id} | endpoint={endpoint}")
    last_log = None

    while time.time() - start < timeout_s:
        status = handler.status(with_logs=True)
        status_name = getattr(status, "status", status.__class__.__name__).upper()

        if isinstance(status, getattr(fal_client, "Queued", tuple())):
            pos = getattr(status, "position", None)
            print(f"   ⏳ fila fal: {status_name} pos={pos}")
        elif isinstance(status, getattr(fal_client, "InProgress", tuple())):
            logs = getattr(status, "logs", None) or []
            if logs:
                msg = logs[-1].get("message") or str(logs[-1])
                if msg != last_log:
                    print(f"   ⏳ fal: {msg}")
                    last_log = msg
            else:
                print(f"   ⏳ fal: {status_name}")
        elif isinstance(status, getattr(fal_client, "Completed", tuple())) or status_name == "COMPLETED":
            payload = handler.get()
            data = _fal_unwrap(payload)
            return {"success": True, "request_id": request_id, "result": data}
        elif status_name in {"FAILED", "ERROR", "CANCELLED"}:
            raise RuntimeError(f"fal request {request_id} terminou com status {status_name}")

        time.sleep(FAL_POLL_INTERVAL_SECONDS)

    raise TimeoutError(f"fal timeout ({timeout_s}s) endpoint={endpoint} request_id={request_id}")


def _content_type_for_path(path: str) -> str:
    return mimetypes.guess_type(path)[0] or "application/octet-stream"


def upload_to_r2(local_path: str, r2_key: str) -> Optional[str]:
    try:
        r2_client = get_r2_client()
        if not r2_client:
            return None
        with open(local_path, 'rb') as f:
            r2_client.put_object(
                Bucket=R2_BUCKET_NAME,
                Key=r2_key,
                Body=f,
                ContentType=_content_type_for_path(local_path)
            )
        public_url = f"{R2_PUBLIC_URL}/{r2_key}" if R2_PUBLIC_URL else None
        if public_url:
            print(f"✅ Uploaded to R2: {public_url}")
        return public_url
    except Exception as e:
        print(f"❌ R2 upload error: {e}")
        return None


def _download_file(url: str, out_path: str, timeout: int = 180) -> bool:
    try:
        with requests.get(url, timeout=timeout, stream=True) as resp:
            if resp.status_code != 200:
                print(f"   ❌ download fal HTTP {resp.status_code}")
                return False
            with open(out_path, "wb") as f:
                for chunk in resp.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)
        return True
    except Exception as e:
        print(f"   ❌ download fal error: {e}")
        return False


def _ensure_public_url(local_path: str, job_id: str, tag: str) -> Optional[str]:
    ext = os.path.splitext(local_path)[1].lower() or ".jpg"
    key = f"jobs/{job_id or 'adhoc'}/refs/{tag}{ext}"
    return upload_to_r2(local_path, key)


def _resolution_map(resolution: str) -> str:
    return {
        "720p": "1K",
        "1080p": "2K",
    }.get((resolution or "720p").lower(), "1K")


def _style_prefix(style: str) -> str:
    return (VISUAL_STYLES.get(style) or VISUAL_STYLES["realistic"])["prefix"]


def _generate_fal_image(
    prompt: str,
    scene_number: int,
    style: str,
    aspect_ratio: str,
    resolution: str,
    reference_image_urls: Optional[List[str]] = None,
) -> Optional[str]:
    styled_prompt = f"{_style_prefix(style)}. {prompt}"
    endpoint = FAL_NANO_BANANA_EDIT_MODEL if reference_image_urls else FAL_NANO_BANANA_MODEL
    args: Dict[str, Any] = {
        "prompt": styled_prompt,
        "num_images": 1,
        "aspect_ratio": aspect_ratio if aspect_ratio in {"16:9", "9:16", "1:1", "4:3"} else "auto",
        "output_format": "jpeg",
        "resolution": _resolution_map(resolution),
        "limit_generations": True,
        "safety_tolerance": "4",
    }
    if reference_image_urls:
        args["image_urls"] = reference_image_urls[:3]
        print(f"   🎭 fal Nano Banana edit com {len(reference_image_urls[:3])} referência(s)")
    else:
        print("   🎭 fal Nano Banana text-to-image")

    try:
        res = _fal_submit_and_wait(endpoint, args)
        data = res.get("result", {})
        images = data.get("images") or []
        if images and images[0].get("url"):
            return images[0]["url"]
        print(f"   ❌ fal imagem sem URL retornada")
        return None
    except Exception as e:
        print(f"   ❌ fal geração de imagem falhou: {e}")
        return None


def _generate_placeholder_image(scene_number: int, prompt: str) -> dict:
    img = Image.new('RGB', (1280, 720), color=(40, 40, 50))
    filename = f"scene_{scene_number:03d}_placeholder.jpg"
    local_path = os.path.join(UPLOAD_DIR, filename)
    img.save(local_path)
    return {
        "success": False,
        "scene_number": scene_number,
        "image_path": local_path,
        "image_url": f"/api/files/{filename}",
        "r2_url": None,
        "prompt_used": prompt[:100],
        "prompt": prompt,
        "mode": "placeholder",
        "aspect_ratio": "16:9",
        "resolution": "720p",
        "provider": "fal.ai",
    }


def _download_and_upload(image_url: str, scene_number: int, job_id: str, aspect_ratio: str, resolution: str, mode: str, prompt: str) -> dict:
    try:
        filename = f"scene_{scene_number:03d}.jpg"
        local_path = os.path.join(UPLOAD_DIR, f"{job_id}_{filename}" if job_id else filename)
        if not _download_file(image_url, local_path, timeout=180):
            return _generate_placeholder_image(scene_number, prompt)
        r2_key = f"jobs/{job_id or 'adhoc'}/scene_{scene_number:03d}.jpg"
        r2_url = upload_to_r2(local_path, r2_key)
        print(f"✅ Scene {scene_number} done")
        return {
            "success": True,
            "scene_number": scene_number,
            "image_path": local_path,
            "image_url": r2_url or image_url,
            "r2_url": r2_url,
            "prompt_used": prompt,
            "prompt": prompt,
            "mode": mode,
            "aspect_ratio": aspect_ratio,
            "resolution": resolution,
            "provider": "fal.ai",
        }
    except Exception as e:
        print(f"❌ download/upload error scene {scene_number}: {e}")
        return _generate_placeholder_image(scene_number, prompt)


def generate_scene_image(
    prompt: str,
    scene_number: int,
    style: str = "realistic",
    aspect_ratio: str = "16:9",
    resolution: str = "720p",
    reference_image_path: str = None,
    reference_imgbb_url: str = None,
    reference_imgbb_urls: Optional[list] = None,
    job_id: str = ""
) -> dict:
    print(f"
🎨 Generating scene {scene_number} [{aspect_ratio}, {resolution}, {style}] via fal.ai")

    ref_urls = list(reference_imgbb_urls or [])
    if not ref_urls and reference_imgbb_url:
        ref_urls = [reference_imgbb_url]
    elif not ref_urls and reference_image_path and os.path.exists(reference_image_path):
        url = _ensure_public_url(reference_image_path, job_id or f"scene{scene_number}", f"ref_{scene_number:03d}")
        if url:
            ref_urls = [url]

    img_url = _generate_fal_image(
        prompt=prompt,
        scene_number=scene_number,
        style=style,
        aspect_ratio=aspect_ratio,
        resolution=resolution,
        reference_image_urls=ref_urls if ref_urls else None,
    )
    if not img_url:
        print("   ⚠️ fal Nano Banana falhou — usando placeholder")
        return _generate_placeholder_image(scene_number, prompt)

    mode = "fal-nano-banana-edit" if ref_urls else "fal-nano-banana-text2image"
    return _download_and_upload(img_url, scene_number, job_id, aspect_ratio, resolution, mode, prompt)


def generate_scenes_batch(
    scenes: list,
    style: str = "realistic",
    aspect_ratio: str = "16:9",
    resolution: str = "720p",
    reference_image_path: str = None,
    reference_image_paths: Optional[list] = None,
    job_id: str = ""
) -> list:
    results = []
    successful_count = 0

    print(f"
🎨 Generating {len(scenes)} scene images via fal.ai / Nano Banana...")
    print(f"   Style:        {style}")
    print(f"   Aspect Ratio: {aspect_ratio}")
    print(f"   Resolution:   {resolution}")

    all_ref_paths = reference_image_paths or []
    if not all_ref_paths and reference_image_path:
        all_ref_paths = [reference_image_path]
    all_ref_paths = [p for p in all_ref_paths if p and os.path.exists(p)]

    cached_ref_urls: List[str] = []
    if all_ref_paths:
        print(f"   🎭 {len(all_ref_paths)} imagem(ns) de referência")
        for i, path in enumerate(all_ref_paths[:3]):
            url = _ensure_public_url(path, job_id or 'adhoc', f"ref_{i+1}")
            if url:
                cached_ref_urls.append(url)
                print(f"   ✅ Ref {i+1} cached via R2")
            else:
                print(f"   ⚠️ Ref {i+1} falhou")
        if not cached_ref_urls:
            print("   ⚠️ Nenhuma referência pública disponível — usando text-to-image")

    for scene in scenes:
        state = jobs_cache.get(job_id, {}) if job_id else {}
        if state.get("cancelled"):
            print(f"🛑 Geração cancelada — cena {scene['scene_number']}")
            results.append(_generate_placeholder_image(scene["scene_number"], scene.get("prompt", "")))
            continue

        result = generate_scene_image(
            prompt=scene["prompt"],
            scene_number=scene["scene_number"],
            style=style,
            aspect_ratio=aspect_ratio,
            resolution=resolution,
            reference_image_path=None,
            reference_imgbb_urls=cached_ref_urls if cached_ref_urls else None,
            job_id=job_id,
        )
        if result["success"]:
            successful_count += 1
        results.append(result)

        if job_id and len(results) % 5 == 0:
            try:
                from services.job_store import save_job
                job = jobs_cache.get(job_id, {})
                # mantém prompts já prontos no estado do job
                job["scene_images"] = results
                save_job(job_id, job)
            except Exception as exc:
                print(f"⚠️ Save cenas falhou: {exc}")

    print(f"✅ Generated {successful_count}/{len(scenes)} scenes successfully")
    return results


def upload_to_r2_compat(local_path: str, r2_key: str) -> Optional[str]:
    return upload_to_r2(local_path, r2_key)
