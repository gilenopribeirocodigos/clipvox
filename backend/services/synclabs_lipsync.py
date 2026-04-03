"""
🎤 ClipVox - Sync Labs Lip Sync Service
Substitui kling_lipsync.py + stemsplit_vocals.py em um único serviço.

Vantagens sobre Kling LipSync + StemSplit:
- Sem necessidade de extração de vocals separada (economiza ~$0.10 por música)
- Melhor qualidade para canto em português (modelo treinado em múltiplos idiomas)
- Menor latência (1 chamada ao invés de 2 serviços)
- Endpoint: fal-ai/sync-lipsync
"""

import os
import time
import subprocess
import requests
from typing import Optional, Dict, Any

from config import (
    FAL_KEY,
    FAL_REQUEST_TIMEOUT_SECONDS,
    FAL_POLL_INTERVAL_SECONDS,
    UPLOAD_DIR,
    R2_BUCKET_NAME,
    R2_PUBLIC_URL,
    get_r2_client,
)

try:
    import fal_client
except Exception:
    fal_client = None

SYNCLABS_ENDPOINT = "fal-ai/sync-lipsync"


def _require_fal() -> None:
    if not FAL_KEY:
        raise RuntimeError("FAL_KEY não configurada")
    if fal_client is None:
        raise RuntimeError("fal-client não instalado")


def _fal_unwrap(result: Any) -> Dict[str, Any]:
    if isinstance(result, dict) and isinstance(result.get("data"), dict):
        return result["data"]
    return result if isinstance(result, dict) else {}


def _ffprobe_duration(path: str) -> float:
    out = subprocess.check_output([
        "ffprobe", "-v", "error",
        "-show_entries", "format=duration",
        "-of", "default=noprint_wrappers=1:nokey=1",
        path,
    ], text=True).strip()
    return float(out)


def _get_duration(path: str) -> float:
    try:
        return _ffprobe_duration(path)
    except Exception:
        return 5.0


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
        raise RuntimeError("Falha ao baixar vídeo de entrada para lipsync")
    return local_path


def _ensure_local_audio(audio_source: str, job_id: str) -> str:
    if os.path.exists(str(audio_source)):
        return str(audio_source)
    ext = os.path.splitext(str(audio_source))[1].lower() or ".mp3"
    local_path = os.path.join(UPLOAD_DIR, f"{job_id}_audio_src{ext}")
    if not _download_to_local(audio_source, local_path, timeout=300):
        raise RuntimeError("Falha ao baixar áudio de entrada para lipsync")
    return local_path


def _normalize_audio(audio_path: str, job_id: str, duration_cap: Optional[float] = None) -> str:
    """
    Normaliza o áudio para MP3 mono 44100Hz.
    Sync Labs aceita o áudio completo da música — não precisa de vocals isolados.
    """
    out_path = os.path.join(UPLOAD_DIR, f"{job_id}_sync_audio.mp3")
    cmd = ["ffmpeg", "-y", "-i", audio_path]
    if duration_cap:
        cmd += ["-t", f"{duration_cap:.2f}"]
    cmd += [
        "-vn",
        "-ar", "44100",
        "-ac", "1",
        "-c:a", "libmp3lame",
        "-b:a", "128k",
        out_path,
    ]
    subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    if not os.path.exists(out_path) or os.path.getsize(out_path) < 1024:
        raise RuntimeError("Áudio normalizado inválido")
    return out_path


def _upload_to_r2(local_path: str, key: str) -> Optional[str]:
    try:
        r2 = get_r2_client()
        if not r2:
            return None
        import mimetypes
        ct = mimetypes.guess_type(local_path)[0] or "application/octet-stream"
        with open(local_path, "rb") as f:
            r2.put_object(Bucket=R2_BUCKET_NAME, Key=key, Body=f, ContentType=ct)
        return f"{R2_PUBLIC_URL}/{key}" if R2_PUBLIC_URL else None
    except Exception as e:
        print(f"   ⚠️ R2 upload error: {e}")
        return None


def _check_url(url: str, label: str) -> bool:
    try:
        resp = requests.head(url, timeout=20, allow_redirects=True)
        if resp.status_code == 405:
            resp = requests.get(url, timeout=20, stream=True)
        ok = 200 <= resp.status_code < 400
        print(f"   {'✅' if ok else '❌'} {label} (HTTP {resp.status_code})")
        return ok
    except Exception as e:
        print(f"   ❌ {label} inacessível: {e}")
        return False


def generate_lipsync(
    face_source: str,
    audio_source: str,
    job_id: str = "",
    model: str = "sync",          # ignorado — sempre usa Sync Labs
    preextracted_vocals: Optional[str] = None,  # ignorado — Sync Labs não precisa
    origin_task_id: str = "",
) -> Dict[str, Any]:
    """
    Interface idêntica ao kling_lipsync.generate_lipsync —
    pode ser substituído diretamente no videos.py sem outras mudanças.

    Sync Labs aceita o áudio completo da música (não precisa de vocals isolados).
    Internamente o modelo identifica e sincroniza a voz automaticamente.
    """
    try:
        _require_fal()
        safe_job_id = job_id or f"sync_{int(time.time())}"
        print(f"🎤 Sync Labs Lip Sync ({SYNCLABS_ENDPOINT}) — job {safe_job_id[:8]}...")

        # 1. Garantir vídeo local e medir duração
        video_local   = _ensure_local_video(face_source, safe_job_id)
        video_duration = _get_duration(video_local)
        print(f"   ⏱️ Vídeo: {video_duration:.2f}s")

        # 2. Usar áudio original completo (Sync Labs não precisa de vocals isolados)
        #    preextracted_vocals é ignorado intencionalmente
        audio_local = _ensure_local_audio(audio_source, safe_job_id)
        audio_duration = _get_duration(audio_local)
        print(f"   🎵 Áudio: {audio_duration:.2f}s (completo, sem separação de vocals)")

        # 3. Normalizar áudio — cortar no tamanho do vídeo
        final_audio = _normalize_audio(audio_local, safe_job_id, duration_cap=video_duration)
        print(f"   ✅ Áudio normalizado: {_get_duration(final_audio):.2f}s")

        # 4. Garantir URLs públicas no R2
        if isinstance(face_source, str) and face_source.startswith(("http://", "https://")):
            video_url = face_source
        else:
            video_url = _upload_to_r2(video_local, f"jobs/{safe_job_id}/lipsync_input.mp4")

        audio_url = _upload_to_r2(final_audio, f"audio/{safe_job_id}/sync_audio.mp3")

        if not video_url or not audio_url:
            return {"success": False, "error": "Falha ao publicar arquivos no R2"}

        if not _check_url(video_url, "Vídeo"):
            return {"success": False, "error": "Vídeo não acessível pelo Sync Labs"}
        if not _check_url(audio_url, "Áudio"):
            return {"success": False, "error": "Áudio não acessível pelo Sync Labs"}

        # 5. Submeter tarefa ao Sync Labs via fal.ai
        print(f"   🚀 Submetendo ao Sync Labs...")
        arguments = {
            "video_url": video_url,
            "audio_url": audio_url,
            # model: "sync-1.6.0" é o padrão do fal-ai/sync-lipsync
            # deixar sem especificar usa o melhor modelo disponível
        }
        handler = fal_client.submit(SYNCLABS_ENDPOINT, arguments=arguments)
        request_id = getattr(handler, "request_id", "")
        print(f"   ✅ Task criada: {request_id}")

        # 6. Polling
        result = _poll(handler, timeout=FAL_REQUEST_TIMEOUT_SECONDS)
        if not result.get("success"):
            return {"success": False, "error": result.get("error", "Sync Labs falhou")}

        final_video_url = result["video_url"]
        print(f"   ✅ Lip sync concluído: {final_video_url[:80]}")

        # 7. Baixar e salvar no R2
        local_out = os.path.join(UPLOAD_DIR, f"{safe_job_id}_lipsync.mp4")
        _download_to_local(final_video_url, local_out, timeout=600)
        r2_url = _upload_to_r2(local_out, f"lipsync/{safe_job_id}/lipsync.mp4") if os.path.exists(local_out) else None

        return {
            "success": True,
            "video_url": r2_url or final_video_url,
            "provider_url": final_video_url,
            "task_id": request_id,
            "provider": "fal.ai / Sync Labs",
            "model_endpoint": SYNCLABS_ENDPOINT,
        }

    except Exception as e:
        import traceback; traceback.print_exc()
        return {"success": False, "error": str(e)}


def _poll(handler: Any, timeout: int = FAL_REQUEST_TIMEOUT_SECONDS) -> Dict[str, Any]:
    start    = time.time()
    last_log = None

    while time.time() - start < timeout:
        try:
            status      = handler.status(with_logs=True)
            status_name = getattr(status, "status", status.__class__.__name__).upper()
            elapsed     = int(time.time() - start)

            if isinstance(status, getattr(fal_client, "Queued", tuple())):
                pos = getattr(status, "position", "?")
                print(f"   ⏳ Sync Labs fila pos={pos} ({elapsed}s)")

            elif isinstance(status, getattr(fal_client, "InProgress", tuple())):
                logs = getattr(status, "logs", None) or []
                if logs:
                    msg = logs[-1].get("message") or str(logs[-1])
                    if msg != last_log:
                        print(f"   ⏳ Sync Labs: {msg} ({elapsed}s)")
                        last_log = msg
                else:
                    print(f"   ⏳ Sync Labs processando... ({elapsed}s)")

            elif isinstance(status, getattr(fal_client, "Completed", tuple())) or status_name == "COMPLETED":
                payload = handler.get()
                data    = _fal_unwrap(payload)

                # Sync Labs retorna { "video": { "url": "..." } }
                video = data.get("video") or {}
                url   = video.get("url") if isinstance(video, dict) else None

                # Fallback: alguns resultados retornam diretamente output_url
                if not url:
                    url = data.get("output_url") or data.get("video_url")

                if url:
                    return {"success": True, "video_url": url}
                return {"success": False, "error": "Sync Labs concluiu sem video.url"}

            elif status_name in {"FAILED", "ERROR", "CANCELLED"}:
                error_msg = None
                try:
                    payload   = handler.get()
                    data      = _fal_unwrap(payload)
                    error_msg = data.get("error") or data.get("message")
                except Exception:
                    pass
                return {"success": False, "error": error_msg or f"Sync Labs falhou: {status_name}"}

        except Exception as e:
            print(f"   ⚠️ Polling erro: {e}")

        time.sleep(FAL_POLL_INTERVAL_SECONDS)

    return {"success": False, "error": f"Sync Labs timeout ({timeout}s)"}
