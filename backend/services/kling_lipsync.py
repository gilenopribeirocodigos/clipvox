"""
🎤 ClipVox - Lip Sync Service (fal.ai / LatentSync)
Mantém a mesma interface do serviço anterior para não quebrar o restante do backend.
"""

import mimetypes
import os
import subprocess
import time
from typing import Optional, Dict, Any, Tuple

import requests

from config import (
    FAL_KEY,
    FAL_LIPSYNC_MODEL,
    FAL_LIPSYNC_GUIDANCE_SCALE,
    FAL_LIPSYNC_LOOP_MODE,
    FAL_REQUEST_TIMEOUT_SECONDS,
    FAL_POLL_INTERVAL_SECONDS,
    UPLOAD_DIR,
    R2_BUCKET_NAME,
    R2_PUBLIC_URL,
    get_r2_client,
)

try:
    import fal_client
except Exception:  # pragma: no cover
    fal_client = None


def _require_fal() -> None:
    if not FAL_KEY:
        raise RuntimeError("FAL_KEY não configurada")
    if fal_client is None:
        raise RuntimeError("fal-client não instalado. Adicione fal-client ao requirements.txt")


def _fal_unwrap(result: Any) -> Dict[str, Any]:
    if isinstance(result, dict) and isinstance(result.get("data"), dict):
        return result["data"]
    return result if isinstance(result, dict) else {}


def _content_type_for_path(path: str) -> str:
    return mimetypes.guess_type(path)[0] or "application/octet-stream"


def _get_video_duration(video_path: str) -> float:
    try:
        out = subprocess.check_output([
            "ffprobe", "-v", "error", "-show_entries", "format=duration",
            "-of", "default=noprint_wrappers=1:nokey=1", video_path
        ], text=True).strip()
        return float(out)
    except Exception:
        return 5.0


def _convert_to_mp3(audio_path: str, job_id: str) -> str:
    if audio_path.lower().endswith(".mp3"):
        return audio_path
    mp3_path = os.path.join(UPLOAD_DIR, f"{job_id}_audio.mp3")
    subprocess.run([
        "ffmpeg", "-y", "-i", audio_path,
        "-vn", "-ar", "44100", "-ac", "2", "-b:a", "192k", mp3_path
    ], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    return mp3_path


def _trim_audio(audio_path: str, out_path: str, duration_seconds: float) -> str:
    duration_seconds = max(0.5, float(duration_seconds))
    subprocess.run([
        "ffmpeg", "-y", "-i", audio_path,
        "-t", f"{duration_seconds:.2f}",
        "-vn", "-ar", "44100", "-ac", "2", "-b:a", "192k", out_path
    ], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    return out_path


def _download_to_local(url: str, out_path: str, timeout: int = 300) -> bool:
    try:
        with requests.get(url, timeout=timeout, stream=True) as resp:
            if resp.status_code != 200:
                return False
            with open(out_path, "wb") as f:
                for chunk in resp.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)
        return True
    except Exception as e:
        print(f"   ❌ download error: {e}")
        return False


def _ensure_local_video(face_source: str, job_id: str) -> str:
    if os.path.exists(str(face_source)):
        return str(face_source)
    local_path = os.path.join(UPLOAD_DIR, f"{job_id}_face.mp4")
    if not _download_to_local(face_source, local_path, timeout=300):
        raise RuntimeError("Falha ao baixar o vídeo de entrada para lipsync")
    return local_path


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
        print(f"   ⚠️ upload R2 error: {e}")
        return None


def _check_url_accessible(url: str, label: str) -> bool:
    try:
        resp = requests.head(url, timeout=30, allow_redirects=True)
        if resp.status_code == 405:
            resp = requests.get(url, timeout=30, allow_redirects=True, stream=True)
        ok = 200 <= resp.status_code < 400
        print(f"   {'✅' if ok else '❌'} {label} acessível (HTTP {resp.status_code})")
        return ok
    except Exception as e:
        print(f"   ❌ {label} inacessível: {e}")
        return False


def create_lipsync_task(video_url: str, audio_url: str, model: str = "latentsync", origin_task_id: str = "") -> Tuple[Optional[str], Optional[Any]]:
    _require_fal()
    endpoint = FAL_LIPSYNC_MODEL
    arguments = {
        "video_url": video_url,
        "audio_url": audio_url,
        "guidance_scale": FAL_LIPSYNC_GUIDANCE_SCALE,
        "loop_mode": FAL_LIPSYNC_LOOP_MODE,
    }
    handler = fal_client.submit(endpoint, arguments=arguments)
    request_id = getattr(handler, "request_id", "")
    print(f"   ✅ fal lipsync task criada: {request_id}")
    return request_id, handler


def poll_lipsync_task(handler: Any, timeout: int = FAL_REQUEST_TIMEOUT_SECONDS) -> Dict[str, Any]:
    start = time.time()
    last_log = None
    while time.time() - start < timeout:
        status = handler.status(with_logs=True)
        status_name = getattr(status, "status", status.__class__.__name__).upper()
        elapsed = int(time.time() - start)
        if isinstance(status, getattr(fal_client, "Queued", tuple())):
            pos = getattr(status, "position", None)
            print(f"   ⏳ lipsync fila pos={pos} ({elapsed}s)")
        elif isinstance(status, getattr(fal_client, "InProgress", tuple())):
            logs = getattr(status, "logs", None) or []
            if logs:
                msg = logs[-1].get("message") or str(logs[-1])
                if msg != last_log:
                    print(f"   ⏳ lipsync: {msg} ({elapsed}s)")
                    last_log = msg
            else:
                print(f"   ⏳ lipsync processing ({elapsed}s)")
        elif isinstance(status, getattr(fal_client, "Completed", tuple())) or status_name == "COMPLETED":
            payload = handler.get()
            data = _fal_unwrap(payload)
            video = data.get("video") or {}
            url = video.get("url") if isinstance(video, dict) else None
            if url:
                return {"success": True, "video_url": url}
            return {"success": False, "error": "fal lipsync concluiu sem video.url"}
        elif status_name in {"FAILED", "ERROR", "CANCELLED"}:
            return {"success": False, "error": f"fal lipsync failed: {status_name}"}
        time.sleep(FAL_POLL_INTERVAL_SECONDS)
    return {"success": False, "error": f"fal lipsync timeout ({timeout}s)"}


def generate_lipsync(
    face_source: str,
    audio_source: str,
    job_id: str = "",
    model: str = "latentsync",
    preextracted_vocals: Optional[str] = None,
    origin_task_id: str = "",
) -> Dict[str, Any]:
    try:
        print(f"🎤 Lip Sync via fal.ai ({FAL_LIPSYNC_MODEL})...")
        video_local = _ensure_local_video(face_source, job_id or 'adhoc')
        video_duration = _get_video_duration(video_local)
        print(f"   ⏱️ Duração do vídeo detectada: {video_duration:.2f}s")

        vocals_path = preextracted_vocals or audio_source
        if not vocals_path or not os.path.exists(str(vocals_path)):
            if os.path.exists(str(audio_source)):
                vocals_path = str(audio_source)
            else:
                raise RuntimeError("Áudio/vocals não disponível localmente para o lipsync")

        mp3_path = _convert_to_mp3(vocals_path, job_id or 'adhoc')
        trimmed_path = os.path.join(UPLOAD_DIR, f"{job_id}_trimmed.mp3")
        _trim_audio(mp3_path, trimmed_path, video_duration)
        print(f"   ✅ Áudio trimado para {video_duration:.2f}s")

        video_url = face_source
        if not (isinstance(video_url, str) and video_url.startswith(("http://", "https://"))):
            video_url = _upload_file_to_r2(video_local, f"jobs/{job_id or 'adhoc'}/lipsync_input.mp4")
        audio_url = _upload_file_to_r2(trimmed_path, f"audio/{job_id or 'adhoc'}/trimmed.mp3")
        if not video_url or not audio_url:
            return {"success": False, "error": "Falha ao publicar arquivos no R2"}

        _check_url_accessible(video_url, "Vídeo")
        _check_url_accessible(audio_url, "Áudio")

        request_id, handler = create_lipsync_task(video_url, audio_url, model=model, origin_task_id=origin_task_id)
        if not request_id or handler is None:
            return {"success": False, "error": "Falha ao criar task de lipsync na fal.ai"}

        result = poll_lipsync_task(handler)
        if not result.get("success"):
            return result

        final_video_url = result["video_url"]
        local_out = os.path.join(UPLOAD_DIR, f"{job_id}_lipsync.mp4")
        _download_to_local(final_video_url, local_out, timeout=600)
        r2_url = _upload_file_to_r2(local_out, f"lipsync/{job_id or 'adhoc'}/lipsync.mp4") if os.path.exists(local_out) else None
        return {
            "success": True,
            "video_url": r2_url or final_video_url,
            "provider_url": final_video_url,
            "task_id": request_id,
            "provider": "fal.ai",
        }
    except Exception as e:
        print(f"   ❌ Exceção fal lipsync: {e}")
        return {"success": False, "error": str(e)}
