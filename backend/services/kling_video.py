"""
🎬 ClipVox - Kling Video Service (fal.ai)
Mantém a interface do serviço antigo, mas usa fal.ai/Kling image-to-video.
"""

import mimetypes
import os
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Optional, Dict, Any, Tuple

import requests

from config import (
    FAL_KEY,
    FAL_KLING_VIDEO_MODEL,
    FAL_REQUEST_TIMEOUT_SECONDS,
    FAL_POLL_INTERVAL_SECONDS,
    FAL_KLING_MAX_WORKERS,
    UPLOAD_DIR,
    R2_BUCKET_NAME,
    R2_PUBLIC_URL,
    get_r2_client,
)

try:
    import fal_client
except Exception:  # pragma: no cover
    fal_client = None

KLING_DEFAULT_VERSION = "2.1"
NEGATIVE_PROMPT_DEFAULT = "blur, distort, and low quality"


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
    print(f"   ✅ fal video task criada: {request_id}")
    last_log = None
    while time.time() - start < timeout_s:
        status = handler.status(with_logs=True)
        status_name = getattr(status, "status", status.__class__.__name__).upper()
        if isinstance(status, getattr(fal_client, "Queued", tuple())):
            pos = getattr(status, "position", None)
            print(f"   ⏳ fila fal video: pos={pos}")
        elif isinstance(status, getattr(fal_client, "InProgress", tuple())):
            logs = getattr(status, "logs", None) or []
            if logs:
                msg = logs[-1].get("message") or str(logs[-1])
                if msg != last_log:
                    print(f"   ⏳ fal video: {msg}")
                    last_log = msg
            else:
                print(f"   ⏳ fal video: {status_name}")
        elif isinstance(status, getattr(fal_client, "Completed", tuple())) or status_name == "COMPLETED":
            payload = handler.get()
            return {"success": True, "request_id": request_id, "result": _fal_unwrap(payload)}
        elif status_name in {"FAILED", "ERROR", "CANCELLED"}:
            raise RuntimeError(f"fal video request {request_id} terminou com status {status_name}")
        time.sleep(FAL_POLL_INTERVAL_SECONDS)
    raise TimeoutError(f"fal video timeout ({timeout_s}s) endpoint={endpoint} request_id={request_id}")


def _content_type_for_path(path: str) -> str:
    return mimetypes.guess_type(path)[0] or "application/octet-stream"


def _upload_file_to_r2(local_path: str, key: str) -> Optional[str]:
    try:
        r2_client = get_r2_client()
        if not r2_client:
            return None
        with open(local_path, "rb") as f:
            r2_client.put_object(
                Bucket=R2_BUCKET_NAME,
                Key=key,
                Body=f,
                ContentType=_content_type_for_path(local_path),
            )
        return f"{R2_PUBLIC_URL}/{key}" if R2_PUBLIC_URL else None
    except Exception as e:
        print(f"   ⚠️ Erro upload R2: {e}")
        return None


def rehost_image_imgbb(image_path: str) -> Optional[str]:
    # Compatibilidade com o código existente: agora rehost no R2.
    if not image_path or not os.path.exists(image_path):
        return None
    return _upload_file_to_r2(image_path, f"adhoc/rehost/{os.path.basename(image_path)}")


def _image_to_base64(image_path: str) -> str:
    import base64
    with open(image_path, "rb") as f:
        return base64.b64encode(f.read()).decode("utf-8")


def create_kling_video_task(
    image_url: str,
    prompt: str,
    scene_number: int,
    aspect_ratio: str = "16:9",
    duration: int = 5,
    mode: str = "std",
    model: str = "kling",
    version: str = KLING_DEFAULT_VERSION,
) -> Tuple[Optional[str], Optional[Any]]:
    args: Dict[str, Any] = {
        "prompt": prompt,
        "image_url": image_url,
        "duration": str(duration if duration in (5, 10) else 5),
        "negative_prompt": NEGATIVE_PROMPT_DEFAULT,
        "cfg_scale": 0.5,
    }
    if aspect_ratio in {"16:9", "9:16", "1:1"}:
        args["aspect_ratio"] = aspect_ratio

    endpoint = FAL_KLING_VIDEO_MODEL
    _require_fal()
    handler = fal_client.submit(endpoint, arguments=args)
    request_id = getattr(handler, "request_id", "")
    print(f"   Task criada (fal) cena {scene_number}: {request_id}")
    return request_id, handler


def poll_kling_video(handler: Any, scene_number: int, timeout: int = FAL_REQUEST_TIMEOUT_SECONDS) -> Optional[str]:
    start = time.time()
    last_log = None
    while time.time() - start < timeout:
        status = handler.status(with_logs=True)
        elapsed = int(time.time() - start)
        status_name = getattr(status, "status", status.__class__.__name__).upper()
        if isinstance(status, getattr(fal_client, "Queued", tuple())):
            pos = getattr(status, "position", None)
            print(f"   Cena {scene_number} - queued ({elapsed}s) pos={pos}")
        elif isinstance(status, getattr(fal_client, "InProgress", tuple())):
            logs = getattr(status, "logs", None) or []
            if logs:
                msg = logs[-1].get("message") or str(logs[-1])
                if msg != last_log:
                    print(f"   Cena {scene_number} - processing ({elapsed}s): {msg}")
                    last_log = msg
            else:
                print(f"   Cena {scene_number} - processing ({elapsed}s)")
        elif isinstance(status, getattr(fal_client, "Completed", tuple())) or status_name == "COMPLETED":
            payload = handler.get()
            data = _fal_unwrap(payload)
            video = data.get("video") or {}
            url = video.get("url") if isinstance(video, dict) else None
            if url:
                print(f"   Cena {scene_number} - completed ({elapsed}s)")
                return url
            return None
        elif status_name in {"FAILED", "ERROR", "CANCELLED"}:
            print(f"   Cena {scene_number} - failed ({elapsed}s) {status_name}")
            return None
        time.sleep(FAL_POLL_INTERVAL_SECONDS)
    print(f"   Timeout ({timeout}s) Cena {scene_number}")
    return None


def _download_video(video_url: str, scene_number: int, job_id: str) -> Tuple[Optional[str], Optional[str]]:
    try:
        resp = requests.get(video_url, timeout=180, stream=True)
        if resp.status_code != 200:
            return None, None
        filename = f"clip_{scene_number:03d}.mp4"
        local_path = os.path.join(UPLOAD_DIR, f"job_{job_id}_{filename}" if job_id else filename)
        with open(local_path, "wb") as f:
            for chunk in resp.iter_content(chunk_size=8192):
                if chunk:
                    f.write(chunk)
        print(f"   Video salvo: {local_path}")
        r2_key = f"jobs/{job_id or 'adhoc'}/clip_{scene_number:03d}.mp4"
        r2_url = _upload_file_to_r2(local_path, r2_key)
        return local_path, r2_url
    except Exception as e:
        print(f"   Erro ao baixar video: {e}")
        return None, None


def generate_video_clip(
    image_path: str = "",
    image_url: str = "",
    prompt: str = "",
    scene_number: int = 1,
    aspect_ratio: str = "16:9",
    duration: int = 5,
    mode: str = "std",
    model: str = "kling",
    version: str = KLING_DEFAULT_VERSION,
    job_id: str = "",
    max_retries: int = 3,
    scene: dict = None,
    bpm: int = None,
) -> dict:
    if scene and not image_url:
        image_url = scene.get("image_url", "")
        image_path = scene.get("image_path", image_path)
        prompt = scene.get("prompt") or scene.get("prompt_used", prompt)
        scene_number = scene.get("scene_number", scene_number)

    public_url = image_url
    if not public_url or public_url.startswith("/api/") or public_url.startswith("/"):
        if image_path and os.path.exists(image_path):
            public_url = rehost_image_imgbb(image_path)
        if not public_url and image_path and os.path.exists(image_path):
            public_url = f"data:image/jpeg;base64,{_image_to_base64(image_path)}"

    if not public_url:
        return {
            "success": False,
            "scene_number": scene_number,
            "video_url": None,
            "kling_url": None,
            "video_path": None,
            "task_id": None,
            "version": version,
            "error": "Sem imagem pública para gerar o clipe",
        }

    for attempt in range(1, max_retries + 1):
        print(f"\nScene {scene_number} Attempt {attempt}/{max_retries} (fal.ai)")
        try:
            task_id, handler = create_kling_video_task(
                image_url=public_url,
                prompt=prompt,
                scene_number=scene_number,
                aspect_ratio=aspect_ratio,
                duration=duration,
                mode=mode,
                model=model,
                version=version,
            )
            if not task_id or handler is None:
                time.sleep(10 * attempt)
                continue
            kling_url = poll_kling_video(handler, scene_number)
            if kling_url:
                local_path, r2_url = _download_video(kling_url, scene_number, job_id)
                final_url = r2_url or kling_url
                print(f"   🔗 fal video_url salva para lip sync: {kling_url[:80]}")
                return {
                    "success": True,
                    "scene_number": scene_number,
                    "video_url": final_url,
                    "kling_url": kling_url,
                    "video_path": local_path,
                    "task_id": task_id,
                    "attempt": attempt,
                    "version": version,
                    "mode": mode,
                    "provider": "fal.ai",
                    "prompt": prompt,
                }
        except Exception as e:
            print(f"   ⚠️ fal video attempt {attempt} erro: {e}")
        time.sleep(10 * attempt)

    return {
        "success": False,
        "scene_number": scene_number,
        "video_url": None,
        "kling_url": None,
        "video_path": None,
        "task_id": None,
        "version": version,
        "error": f"Falhou apos {max_retries} tentativas",
        "provider": "fal.ai",
        "prompt": prompt,
    }


def generate_video_clips_batch(
    scenes: list,
    aspect_ratio: str = "16:9",
    duration: int = 5,
    mode: str = "std",
    model: str = "kling",
    version: str = KLING_DEFAULT_VERSION,
    job_id: str = "",
    bpm: int = None,
    **kwargs
) -> list:
    total = len(scenes)
    print(f"\nGenerating {total} video clips via fal.ai / Kling ...")
    print(f"   Mode: {mode} | {duration}s | {aspect_ratio} | workers={FAL_KLING_MAX_WORKERS}")

    max_workers = max(1, min(FAL_KLING_MAX_WORKERS, total))
    results: list = []
    if max_workers == 1:
        for scene in scenes:
            results.append(
                generate_video_clip(
                    image_path=scene.get("image_path", ""),
                    image_url=scene.get("image_url", ""),
                    prompt=scene.get("prompt") or scene.get("prompt_used", ""),
                    scene_number=scene.get("scene_number", 0),
                    aspect_ratio=aspect_ratio,
                    duration=duration,
                    mode=mode,
                    model=model,
                    version=version,
                    job_id=job_id,
                    bpm=bpm,
                )
            )
        return results

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futs = {
            executor.submit(
                generate_video_clip,
                scene.get("image_path", ""),
                scene.get("image_url", ""),
                scene.get("prompt") or scene.get("prompt_used", ""),
                scene.get("scene_number", 0),
                aspect_ratio,
                duration,
                mode,
                model,
                version,
                job_id,
                3,
                None,
                bpm,
            ): scene.get("scene_number", 0)
            for scene in scenes
        }
        for future in as_completed(futs):
            results.append(future.result())
    return sorted(results, key=lambda x: x.get("scene_number", 0))


generate_videos_batch = generate_video_clips_batch
