"""
🎤 ClipVox - Demucs + Sync Labs (Máxima Precisão)

Pipeline:
  1. fal-ai/demucs              → extrai APENAS vocals (sem bateria, violão, etc)
  2. fal-ai/sync-lipsync → lipsync-1.8.0 (principal) → lipsync-1.7.1 (fallback)
     fallback: fal-ai/sync-lipsync → lipsync-1.7.1

Interface idêntica — troca direta, sem mudanças no videos.py.
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

DEMUCS_ENDPOINT = "fal-ai/demucs"

# Cascata: (endpoint, model_param_or_None)
# lipsync-1.7.1:      fallback estável
# lipsync-1.9.0-beta REMOVIDO: desfigura o rosto (artefatos graves)
# lipsync-2         REMOVIDO: distorce para canto (feito para fala/dublagem)
# react-1           REMOVIDO: $10/min sem ganho de qualidade
SYNCLABS_CASCADE = [
    ("fal-ai/sync-lipsync", "lipsync-1.8.0"),  # principal — estável, sem artefatos
    ("fal-ai/sync-lipsync", "lipsync-1.7.1"),  # fallback
]


# ══════════════════════════════════════════════════════
# UTILITÁRIOS GERAIS
# ══════════════════════════════════════════════════════

def _require_fal() -> None:
    if not FAL_KEY:
        raise RuntimeError("FAL_KEY não configurada")
    if fal_client is None:
        raise RuntimeError("fal-client não instalado. Adicione fal-client ao requirements.txt")


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


def _get_duration(path: str, fallback: float = 5.0) -> float:
    try:
        return _ffprobe_duration(path)
    except Exception:
        return fallback


def _download_to_local(url: str, out_path: str, timeout: int = 300) -> bool:
    try:
        with requests.get(url, timeout=timeout, stream=True) as resp:
            if resp.status_code != 200:
                print(f"   ❌ Download HTTP {resp.status_code}: {url[:80]}")
                return False
            with open(out_path, "wb") as f:
                for chunk in resp.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)
        return True
    except Exception as e:
        print(f"   ❌ Download error: {e}")
        return False


def _ensure_local_video(source: str, job_id: str) -> str:
    if os.path.exists(str(source)):
        return str(source)
    local = os.path.join(UPLOAD_DIR, f"{job_id}_face.mp4")
    if not _download_to_local(source, local, timeout=300):
        raise RuntimeError("Falha ao baixar vídeo para lipsync")
    return local


def _ensure_local_audio(source: str, job_id: str) -> str:
    if os.path.exists(str(source)):
        return str(source)
    ext   = os.path.splitext(str(source))[1].lower() or ".mp3"
    local = os.path.join(UPLOAD_DIR, f"{job_id}_audio_src{ext}")
    if not _download_to_local(source, local, timeout=300):
        raise RuntimeError("Falha ao baixar áudio para lipsync")
    return local


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


def _normalize_audio(audio_path: str, job_id: str,
                     duration_cap: Optional[float] = None,
                     suffix: str = "norm") -> str:
    """MP3 mono 44100 Hz — corta no tamanho do vídeo se duration_cap fornecido."""
    out = os.path.join(UPLOAD_DIR, f"{job_id}_{suffix}.mp3")
    cmd = ["ffmpeg", "-y", "-i", audio_path]
    if duration_cap:
        cmd += ["-t", f"{duration_cap:.3f}"]
    cmd += ["-vn", "-ar", "44100", "-ac", "1",
            "-c:a", "libmp3lame", "-b:a", "128k", out]
    subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    if not os.path.exists(out) or os.path.getsize(out) < 1024:
        raise RuntimeError("Áudio normalizado inválido")
    return out


# ══════════════════════════════════════════════════════
# PASSO 1 — DEMUCS: extração de vocals via fal.ai
# ══════════════════════════════════════════════════════

def _extract_vocals_demucs(audio_url: str, job_id: str) -> Optional[str]:
    """
    fal-ai/demucs recebe só audio_url e retorna stems na raiz:
    data = { "vocals": {"url":"..."}, "drums": {...}, ... }
    """
    print(f"   🎵 Demucs: extraindo vocals de {audio_url[:60]}...")
    try:
        handler    = fal_client.submit(DEMUCS_ENDPOINT, arguments={"audio_url": audio_url})
        request_id = getattr(handler, "request_id", "")
        print(f"   ⏳ Demucs task: {request_id}")

        start    = time.time()
        timeout  = 300
        last_log = None

        while time.time() - start < timeout:
            status      = handler.status(with_logs=True)
            status_name = getattr(status, "status", status.__class__.__name__).upper()
            elapsed     = int(time.time() - start)

            if isinstance(status, getattr(fal_client, "Queued", tuple())):
                print(f"   ⏳ Demucs fila pos={getattr(status,'position','?')} ({elapsed}s)")
            elif isinstance(status, getattr(fal_client, "InProgress", tuple())):
                logs = getattr(status, "logs", None) or []
                if logs:
                    msg = logs[-1].get("message") or str(logs[-1])
                    if msg != last_log:
                        print(f"   ⏳ Demucs: {msg} ({elapsed}s)")
                        last_log = msg
                else:
                    print(f"   ⏳ Demucs processando... ({elapsed}s)")
            elif isinstance(status, getattr(fal_client, "Completed", tuple())) or status_name == "COMPLETED":
                payload   = handler.get()
                data      = _fal_unwrap(payload)
                vocals    = data.get("vocals") or {}
                vocal_url = vocals.get("url") if isinstance(vocals, dict) else None
                if not vocal_url:
                    stems     = data.get("stems") or {}
                    vocals_s  = stems.get("vocals") or {}
                    vocal_url = vocals_s.get("url") if isinstance(vocals_s, dict) else None
                if not vocal_url:
                    vocal_url = data.get("vocals_url") or data.get("vocal_url")
                if vocal_url:
                    print(f"   ✅ Demucs vocals extraídos: {vocal_url[:80]}")
                    return vocal_url
                print(f"   ❌ Demucs sem vocal_url. Keys: {list(data.keys())}")
                return None
            elif status_name in {"FAILED", "ERROR", "CANCELLED"}:
                print(f"   ❌ Demucs falhou: {status_name}")
                return None

            time.sleep(FAL_POLL_INTERVAL_SECONDS)

        print(f"   ❌ Demucs timeout ({timeout}s)")
        return None

    except Exception as e:
        print(f"   ❌ Demucs exception: {e}")
        return None


# ══════════════════════════════════════════════════════
# PASSO 2 — SYNC LABS com cascata de modelos
# ══════════════════════════════════════════════════════

_RETRYABLE_ERRORS = (
    "downstream_service_unavailable",
    "downstream service unavailable",
    "504", "502", "503",
    "gateway timeout",
    "upstream connect error",
)

def _is_retryable(error_str: str) -> bool:
    low = (error_str or "").lower()
    return any(k in low for k in _RETRYABLE_ERRORS)


def _try_single_endpoint(video_url: str, audio_url: str,
                         endpoint: str, model: Optional[str],
                         timeout: int, max_retries: int) -> Dict[str, Any]:
    """Tenta lipsync em UM endpoint/modelo com retry para erros transitórios."""
    label      = f"{endpoint} [{model}]" if model else endpoint
    last_error = f"{label} falhou"

    for attempt in range(1, max_retries + 1):
        if attempt > 1:
            wait = 15 * attempt
            print(f"      ↩ retry {attempt}/{max_retries} em {wait}s ({label})...")
            time.sleep(wait)

        try:
            print(f"   🎤 {label}: tentativa {attempt}/{max_retries}...")
            args = {"video_url": video_url, "audio_url": audio_url}
            if model:
                args["model"] = model

            handler    = fal_client.submit(endpoint, arguments=args)
            request_id = getattr(handler, "request_id", "")
            print(f"   ⏳ task: {request_id}")

            start    = time.time()
            last_log = None

            while time.time() - start < timeout:
                try:
                    status      = handler.status(with_logs=True)
                    status_name = getattr(status, "status", status.__class__.__name__).upper()
                    elapsed     = int(time.time() - start)

                    if isinstance(status, getattr(fal_client, "Queued", tuple())):
                        print(f"   ⏳ fila pos={getattr(status,'position','?')} ({elapsed}s)")
                    elif isinstance(status, getattr(fal_client, "InProgress", tuple())):
                        logs = getattr(status, "logs", None) or []
                        if logs:
                            msg = logs[-1].get("message") or str(logs[-1])
                            if msg != last_log:
                                print(f"   ⏳ {msg} ({elapsed}s)")
                                last_log = msg
                        else:
                            print(f"   ⏳ processando... ({elapsed}s)")
                    elif isinstance(status, getattr(fal_client, "Completed", tuple())) or status_name == "COMPLETED":
                        try:
                            payload = handler.get()
                        except Exception as get_err:
                            err_str = str(get_err)
                            print(f"   ⚠️ get() erro: {err_str[:120]}")
                            last_error = err_str
                            if _is_retryable(err_str):
                                break
                            return {"success": False, "retryable": False, "error": err_str}

                        data  = _fal_unwrap(payload)
                        video = data.get("video") or {}
                        url   = video.get("url") if isinstance(video, dict) else None
                        if not url:
                            url = data.get("output_url") or data.get("video_url")
                        if url:
                            print(f"   ✅ {label} concluído: {url[:80]}")
                            return {"success": True, "video_url": url,
                                    "task_id": request_id, "model_used": label}
                        return {"success": False, "retryable": False,
                                "error": f"{label} concluiu sem video.url"}

                    elif status_name in {"FAILED", "ERROR", "CANCELLED"}:
                        err_msg = None
                        try:
                            payload = handler.get()
                            data    = _fal_unwrap(payload)
                            err_msg = data.get("error") or data.get("message")
                        except Exception:
                            pass
                        err        = err_msg or f"{label}: {status_name}"
                        last_error = err
                        if _is_retryable(err):
                            break
                        return {"success": False, "retryable": False, "error": err}

                except Exception as poll_err:
                    err_str    = str(poll_err)
                    last_error = err_str
                    print(f"   ⚠️ polling erro: {err_str[:120]}")
                    if _is_retryable(err_str):
                        break
                    return {"success": False, "retryable": False, "error": err_str}

                time.sleep(FAL_POLL_INTERVAL_SECONDS)
            else:
                last_error = f"{label} timeout ({timeout}s)"
                print(f"   ⚠️ {last_error}")

        except Exception as submit_err:
            err_str    = str(submit_err)
            last_error = err_str
            print(f"   ⚠️ submit erro: {err_str[:120]}")
            if not _is_retryable(err_str):
                return {"success": False, "retryable": False, "error": err_str}

    return {"success": False, "retryable": True, "error": last_error}


def _run_synclabs(video_url: str, audio_url: str,
                  timeout: int = FAL_REQUEST_TIMEOUT_SECONDS,
                  max_retries: int = 2) -> Dict[str, Any]:
    """
    Cascata: lipsync-1.8.0 → lipsync-1.7.1 (fallback)
    """
    for endpoint, model in SYNCLABS_CASCADE:
        label = f"{endpoint} [{model}]" if model else endpoint
        print(f"\n   🔀 Tentando: {label}")
        result = _try_single_endpoint(video_url, audio_url, endpoint, model, timeout, max_retries)
        if result["success"]:
            return result
        if not result.get("retryable", False):
            print(f"   ❌ Erro definitivo em {label}: {result['error'][:80]}")
            return result
        print(f"   ⚠️ {label} indisponível — tentando próximo...")

    return {"success": False,
            "error": "Todos os modelos Sync Labs indisponíveis. Tente novamente mais tarde."}


# ══════════════════════════════════════════════════════
# FUNÇÃO PRINCIPAL
# ══════════════════════════════════════════════════════

def generate_lipsync(
    face_source: str,
    audio_source: str,
    job_id: str = "",
    model: str = "sync",
    preextracted_vocals: Optional[str] = None,
    origin_task_id: str = "",
) -> Dict[str, Any]:
    """
    Pipeline: Demucs (vocals) → Sync Labs lipsync-1.8.0
    Custo: ~$0.012/seg de vídeo (~$0.06 por clipe de 5s)
    Modelos: lipsync-1.8.0 (principal) → lipsync-1.7.1 (fallback)
    Interface idêntica — troca direta no videos.py sem outras mudanças.
    """
    try:
        _require_fal()
        safe_job_id = job_id or f"sync_{int(time.time())}"
        print(f"\n{'='*60}")
        print(f"🎤 Demucs + Sync Labs lipsync-1.8.0 — job {safe_job_id[:12]}")
        print(f"{'='*60}")

        # 1. Vídeo local + duração
        video_local    = _ensure_local_video(face_source, safe_job_id)
        video_duration = _get_duration(video_local)
        print(f"   ⏱️  Vídeo: {video_duration:.2f}s")

        # 2. Áudio local
        audio_local = _ensure_local_audio(audio_source, safe_job_id)
        print(f"   🎵 Áudio original: {_get_duration(audio_local):.2f}s")

        # 3. Normalizar + subir áudio completo para Demucs
        full_audio_norm = _normalize_audio(audio_local, safe_job_id, suffix="full_norm")
        audio_r2_url    = _upload_to_r2(full_audio_norm, f"audio/{safe_job_id}/full_audio.mp3")
        if not audio_r2_url:
            return {"success": False, "error": "Falha ao publicar áudio no R2"}
        if not _check_url(audio_r2_url, "Áudio para Demucs"):
            return {"success": False, "error": "Áudio não acessível pelo Demucs"}

        # 4. Demucs — extrai vocals
        vocals_url      = _extract_vocals_demucs(audio_r2_url, safe_job_id)
        final_audio_url = audio_r2_url

        if vocals_url:
            vocals_local = os.path.join(UPLOAD_DIR, f"{safe_job_id}_vocals_raw.mp3")
            if _download_to_local(vocals_url, vocals_local, timeout=120):
                vocals_norm   = _normalize_audio(vocals_local, safe_job_id,
                                                 duration_cap=video_duration,
                                                 suffix="vocals_norm")
                vocals_r2_url = _upload_to_r2(vocals_norm, f"audio/{safe_job_id}/vocals.mp3")
                if vocals_r2_url and _check_url(vocals_r2_url, "Vocals Demucs"):
                    print(f"   ✅ Vocals isolados prontos — usando para sync")
                    final_audio_url = vocals_r2_url
                else:
                    print(f"   ⚠️ Vocals R2 falhou — usando áudio completo")
            else:
                print(f"   ⚠️ Download vocals falhou — usando áudio completo")
        else:
            print(f"   ⚠️ Demucs falhou — fallback: áudio completo")

        # 5. URL pública do vídeo
        if isinstance(face_source, str) and face_source.startswith(("http://", "https://")):
            video_url = face_source
        else:
            video_url = _upload_to_r2(video_local, f"jobs/{safe_job_id}/lipsync_input.mp4")
        if not video_url:
            return {"success": False, "error": "Falha ao publicar vídeo no R2"}
        if not _check_url(video_url, "Vídeo para Sync Labs"):
            return {"success": False, "error": "Vídeo não acessível pelo Sync Labs"}

        # 6. Sync Labs
        result = _run_synclabs(video_url, final_audio_url)
        if not result.get("success"):
            return {"success": False, "error": result.get("error", "Sync Labs falhou")}

        final_video_url = result["video_url"]

        # 7. Salvar no R2
        local_out = os.path.join(UPLOAD_DIR, f"{safe_job_id}_lipsync.mp4")
        _download_to_local(final_video_url, local_out, timeout=600)
        r2_url = None
        if os.path.exists(local_out):
            r2_url = _upload_to_r2(local_out, f"lipsync/{safe_job_id}/lipsync.mp4")

        vocals_used = "demucs_vocals" if vocals_url else "full_audio_fallback"
        print(f"   ✅ Lipsync concluído | áudio: {vocals_used} | modelo: {result.get('model_used','?')}")
        print(f"{'='*60}\n")

        return {
            "success":        True,
            "video_url":      r2_url or final_video_url,
            "provider_url":   final_video_url,
            "task_id":        result.get("task_id", ""),
            "provider":       "fal.ai / Demucs + Sync Labs",
            "vocals_source":  vocals_used,
            "model_used":     result.get("model_used", ""),
            "model_endpoint": result.get("model_used", ""),
        }

    except Exception as e:
        import traceback; traceback.print_exc()
        return {"success": False, "error": str(e)}
