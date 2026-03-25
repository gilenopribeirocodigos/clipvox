"""
🎤 ClipVox - Lip Sync Service (fal.ai / Kling LipSync)
Mantém a mesma interface do serviço anterior para não quebrar o restante do backend.

Mudanças principais:
- troca o modelo de lipsync para fal-ai/kling-video/lipsync/audio-to-video
- normaliza o áudio final para MP3 mono, alinhado ao exemplo oficial do modelo
- mantém upload em R2 e retorno compatível com videos.py
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


KLING_LIPSYNC_ENDPOINT = "fal-ai/kling-video/lipsync/audio-to-video"


def _resolve_endpoint() -> str:
    candidate = (os.getenv("FAL_LIPSYNC_MODEL") or FAL_LIPSYNC_MODEL or "").strip()
    # Se ainda estiver vindo latentsync da config antiga, força Kling LipSync.
    if not candidate or "latentsync" in candidate.lower():
        return KLING_LIPSYNC_ENDPOINT
    return candidate


RESOLVED_LIPSYNC_ENDPOINT = _resolve_endpoint()


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
    ext = os.path.splitext(path)[1].lower()
    if ext == ".wav":
        return "audio/wav"
    if ext == ".mp3":
        return "audio/mpeg"
    if ext == ".mp4":
        return "video/mp4"
    return mimetypes.guess_type(path)[0] or "application/octet-stream"


def _ffprobe_duration(path: str) -> float:
    out = subprocess.check_output(
        [
            "ffprobe", "-v", "error",
            "-show_entries", "format=duration",
            "-of", "default=noprint_wrappers=1:nokey=1",
            path,
        ],
        text=True,
    ).strip()
    return float(out)


def _get_video_duration(video_path: str) -> float:
    try:
        return _ffprobe_duration(video_path)
    except Exception:
        return 5.0


def _get_audio_duration(audio_path: str) -> float:
    try:
        return _ffprobe_duration(audio_path)
    except Exception:
        return 0.0


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


def _ensure_local_audio(audio_source: str, job_id: str) -> str:
    if os.path.exists(str(audio_source)):
        return str(audio_source)
    ext = os.path.splitext(str(audio_source))[1].lower() or ".bin"
    local_path = os.path.join(UPLOAD_DIR, f"{job_id}_audio_src{ext}")
    if not _download_to_local(audio_source, local_path, timeout=300):
        raise RuntimeError("Falha ao baixar o áudio de entrada para lipsync")
    return local_path


def _normalize_audio_to_mp3(audio_path: str, out_path: str, duration_seconds: Optional[float] = None) -> str:
    """Converte/normaliza para MP3 mono CBR, alinhado ao exemplo oficial do Kling LipSync."""
    cmd = ["ffmpeg", "-y", "-i", audio_path]
    if duration_seconds is not None:
        cmd += ["-t", f"{max(2.0, float(duration_seconds)):.2f}"]
    cmd += [
        "-vn",
        "-ar", "44100",
        "-ac", "1",
        "-c:a", "libmp3lame",
        "-b:a", "128k",
        out_path,
    ]
    subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    if not os.path.exists(out_path) or os.path.getsize(out_path) < 2048:
        raise RuntimeError("Áudio MP3 gerado inválido ou vazio")

    if os.path.getsize(out_path) > 5 * 1024 * 1024:
        # Ajuste defensivo ao limite do modelo (5 MB)
        smaller = out_path.rsplit(".", 1)[0] + "_64k.mp3"
        cmd2 = [
            "ffmpeg", "-y", "-i", audio_path,
            "-t", f"{max(2.0, float(duration_seconds or 5.0)):.2f}",
            "-vn",
            "-ar", "22050",
            "-ac", "1",
            "-c:a", "libmp3lame",
            "-b:a", "64k",
            smaller,
        ]
        subprocess.run(cmd2, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        if os.path.exists(smaller) and os.path.getsize(smaller) <= 5 * 1024 * 1024:
            return smaller
        raise RuntimeError("Áudio final excede 5 MB, limite do Kling LipSync")

    dur = _get_audio_duration(out_path)
    if dur < 1.9:
        raise RuntimeError("Duração do áudio final ficou abaixo do mínimo do Kling LipSync (2s)")
    return out_path


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


def create_lipsync_task(video_url: str, audio_url: str, model: str = "kling", origin_task_id: str = "") -> Tuple[Optional[str], Optional[Any]]:
    _require_fal()
    endpoint = RESOLVED_LIPSYNC_ENDPOINT
    arguments = {
        "video_url": video_url,
        "audio_url": audio_url,
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
            print(f"   ⏳ kling lipsync fila pos={pos} ({elapsed}s)")
        elif isinstance(status, getattr(fal_client, "InProgress", tuple())):
            logs = getattr(status, "logs", None) or []
            if logs:
                msg = logs[-1].get("message") or str(logs[-1])
                if msg != last_log:
                    print(f"   ⏳ kling lipsync: {msg} ({elapsed}s)")
                    last_log = msg
            else:
                print(f"   ⏳ kling lipsync processing ({elapsed}s)")
        elif isinstance(status, getattr(fal_client, "Completed", tuple())) or status_name == "COMPLETED":
            payload = handler.get()
            data = _fal_unwrap(payload)
            video = data.get("video") or {}
            url = video.get("url") if isinstance(video, dict) else None
            if url:
                return {"success": True, "video_url": url}
            return {"success": False, "error": "Kling LipSync concluiu sem video.url"}
        elif status_name in {"FAILED", "ERROR", "CANCELLED"}:
            error_message = None
            try:
                payload = handler.get()
                data = _fal_unwrap(payload)
                error_message = data.get("error") or data.get("message")
            except Exception:
                pass
            return {"success": False, "error": error_message or f"Kling LipSync failed: {status_name}"}
        time.sleep(FAL_POLL_INTERVAL_SECONDS)
    return {"success": False, "error": f"Kling LipSync timeout ({timeout}s)"}


def generate_lipsync(
    face_source: str,
    audio_source: str,
    job_id: str = "",
    model: str = "kling",
    preextracted_vocals: Optional[str] = None,
    origin_task_id: str = "",
) -> Dict[str, Any]:
    try:
        print(f"🎤 Lip Sync via fal.ai ({RESOLVED_LIPSYNC_ENDPOINT})...")
        safe_job_id = job_id or "adhoc"

        video_local = _ensure_local_video(face_source, safe_job_id)
        video_duration = _get_video_duration(video_local)
        print(f"   ⏱️ Duração do vídeo detectada: {video_duration:.2f}s")

        vocals_source = preextracted_vocals or audio_source
        if not vocals_source:
            raise RuntimeError("Áudio/vocals não informado para o lipsync")

        vocals_local = _ensure_local_audio(vocals_source, safe_job_id)
        source_audio_duration = _get_audio_duration(vocals_local)
        print(f"   🎵 Áudio fonte detectado: {source_audio_duration:.2f}s")

        trimmed_mp3_path = os.path.join(UPLOAD_DIR, f"{safe_job_id}_trimmed.mp3")
        final_audio_path = _normalize_audio_to_mp3(vocals_local, trimmed_mp3_path, video_duration)
        final_audio_duration = _get_audio_duration(final_audio_path)
        print(f"   ✅ Áudio normalizado para MP3 mono: {final_audio_duration:.2f}s")

        video_url = face_source
        if not (isinstance(video_url, str) and video_url.startswith(("http://", "https://"))):
            video_url = _upload_file_to_r2(video_local, f"jobs/{safe_job_id}/lipsync_input.mp4")
        audio_url = _upload_file_to_r2(final_audio_path, f"audio/{safe_job_id}/trimmed.mp3")
        if not video_url or not audio_url:
            return {"success": False, "error": "Falha ao publicar arquivos no R2"}

        if not _check_url_accessible(video_url, "Vídeo"):
            return {"success": False, "error": "Vídeo não acessível para o Kling LipSync"}
        if not _check_url_accessible(audio_url, "Áudio MP3"):
            return {"success": False, "error": "Áudio não acessível para o Kling LipSync"}

        request_id, handler = create_lipsync_task(video_url, audio_url, model=model, origin_task_id=origin_task_id)
        if not request_id or handler is None:
            return {"success": False, "error": "Falha ao criar task de lipsync na fal.ai"}

        result = poll_lipsync_task(handler)
        if not result.get("success"):
            return {"success": False, "error": str(result.get("error", "Falha desconhecida no Kling LipSync"))}

        final_video_url = result["video_url"]
        local_out = os.path.join(UPLOAD_DIR, f"{safe_job_id}_lipsync.mp4")
        _download_to_local(final_video_url, local_out, timeout=600)
        r2_url = _upload_file_to_r2(local_out, f"lipsync/{safe_job_id}/lipsync.mp4") if os.path.exists(local_out) else None
        return {
            "success": True,
            "video_url": r2_url or final_video_url,
            "provider_url": final_video_url,
            "task_id": request_id,
            "provider": "fal.ai",
            "audio_format_sent": "mp3",
            "model_endpoint": RESOLVED_LIPSYNC_ENDPOINT,
        }
    except Exception as e:
        print(f"   ❌ Exceção fal kling lipsync: {e}")
        return {"success": False, "error": str(e)}
