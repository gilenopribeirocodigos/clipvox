"""
🎤 ClipVox - Demucs + Sync Labs v2 (Máxima Precisão)

Pipeline:
  1. fal-ai/demucs   → extrai APENAS vocals (sem bateria, violão, etc)
  2. fal-ai/sync-lipsync (model: sync-2) → lipsync com vocals limpos

Interface idêntica ao synclabs_lipsync.py anterior — troca direta, sem
mudanças no videos.py.
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

DEMUCS_ENDPOINT   = "fal-ai/demucs"
SYNCLABS_ENDPOINT = "fal-ai/sync-lipsync"
SYNCLABS_MODEL    = "lipsync-1.9.0-beta"   # modelo mais recente do fal-ai/sync-lipsync


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
    Chama fal-ai/demucs para separar vocals do resto da música.
    Retorna URL pública dos vocals isolados, ou None se falhar.

    IMPORTANTE: fal-ai/demucs NÃO aceita parâmetro 'stem' ou 'model'.
    Retorna todos os stems separados; pegamos vocals do resultado.
    Resposta: { "stems": { "vocals": {"url":"..."}, "drums": {...}, ... } }
    """
    print(f"   🎵 Demucs: extraindo vocals de {audio_url[:60]}...")
    try:
        handler = fal_client.submit(
            DEMUCS_ENDPOINT,
            arguments={
                "audio_url": audio_url,
                # ✅ Sem 'stem' nem 'model' — a API retorna todos os stems
                # e pegamos só o 'vocals' do resultado
            },
        )
        request_id = getattr(handler, "request_id", "")
        print(f"   ⏳ Demucs task: {request_id}")

        start = time.time()
        timeout = 300
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
                payload = handler.get()
                data    = _fal_unwrap(payload)

                # ✅ fal-ai/demucs retorna os stems diretamente na raiz do resultado:
                # data = { "vocals": {"url":"..."}, "drums": {"url":"..."}, ... }
                # NÃO está aninhado em data["stems"]["vocals"]
                vocals    = data.get("vocals") or {}
                vocal_url = vocals.get("url") if isinstance(vocals, dict) else None

                # Fallback: tenta estrutura aninhada (versões antigas da API)
                if not vocal_url:
                    stems     = data.get("stems") or {}
                    vocals_s  = stems.get("vocals") or {}
                    vocal_url = vocals_s.get("url") if isinstance(vocals_s, dict) else None

                # Fallback 2: campos flat
                if not vocal_url:
                    vocal_url = data.get("vocals_url") or data.get("vocal_url")

                if vocal_url:
                    print(f"   ✅ Demucs vocals extraídos: {vocal_url[:80]}")
                    return vocal_url

                print(f"   ❌ Demucs sem vocal_url. Keys disponíveis: {list(data.keys())}")
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
# PASSO 2 — SYNC LABS: lipsync com vocals limpos
# ══════════════════════════════════════════════════════

def _run_synclabs(video_url: str, audio_url: str,
                  timeout: int = FAL_REQUEST_TIMEOUT_SECONDS) -> Dict[str, Any]:
    """
    Chama fal-ai/sync-lipsync com model=sync-2.
    sync-2 é o modelo mais recente do Sync Labs — treinado para canto,
    melhor em múltiplos idiomas incluindo português.
    """
    print(f"   🎤 Sync Labs {SYNCLABS_MODEL}: sincronizando lábios...")
    handler = fal_client.submit(
        SYNCLABS_ENDPOINT,
        arguments={
            "video_url": video_url,
            "audio_url": audio_url,
            "model":     SYNCLABS_MODEL,   # lipsync-1.9.0-beta — mais preciso
        },
    )
    request_id = getattr(handler, "request_id", "")
    print(f"   ⏳ Sync Labs task: {request_id}")

    start    = time.time()
    last_log = None
    while time.time() - start < timeout:
        status      = handler.status(with_logs=True)
        status_name = getattr(status, "status", status.__class__.__name__).upper()
        elapsed     = int(time.time() - start)

        if isinstance(status, getattr(fal_client, "Queued", tuple())):
            print(f"   ⏳ Sync Labs fila pos={getattr(status,'position','?')} ({elapsed}s)")

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
            video   = data.get("video") or {}
            url     = video.get("url") if isinstance(video, dict) else None
            if not url:
                url = data.get("output_url") or data.get("video_url")
            if url:
                print(f"   ✅ Sync Labs concluído: {url[:80]}")
                return {"success": True, "video_url": url, "task_id": request_id}
            return {"success": False, "error": "Sync Labs concluiu sem video.url"}

        elif status_name in {"FAILED", "ERROR", "CANCELLED"}:
            error_msg = None
            try:
                payload   = handler.get()
                data      = _fal_unwrap(payload)
                error_msg = data.get("error") or data.get("message")
            except Exception:
                pass
            return {"success": False, "error": error_msg or f"Sync Labs: {status_name}"}

        time.sleep(FAL_POLL_INTERVAL_SECONDS)

    return {"success": False, "error": f"Sync Labs timeout ({timeout}s)"}


# ══════════════════════════════════════════════════════
# FUNÇÃO PRINCIPAL — interface idêntica ao serviço anterior
# ══════════════════════════════════════════════════════

def generate_lipsync(
    face_source: str,
    audio_source: str,
    job_id: str = "",
    model: str = "sync",          # ignorado — sempre usa Sync Labs sync-2
    preextracted_vocals: Optional[str] = None,  # ignorado — usamos Demucs
    origin_task_id: str = "",
) -> Dict[str, Any]:
    """
    Pipeline: Demucs (vocal extraction) → Sync Labs sync-2 (lipsync)

    Interface idêntica ao synclabs_lipsync.py anterior e ao kling_lipsync.py —
    pode ser substituído diretamente no videos.py sem nenhuma outra mudança.
    """
    try:
        _require_fal()
        safe_job_id = job_id or f"sync_{int(time.time())}"
        print(f"\n{'='*60}")
        print(f"🎤 Demucs + Sync Labs sync-2 — job {safe_job_id[:12]}")
        print(f"{'='*60}")

        # ── 1. Garantir vídeo local e medir duração ──────────────
        video_local    = _ensure_local_video(face_source, safe_job_id)
        video_duration = _get_duration(video_local)
        print(f"   ⏱️  Vídeo: {video_duration:.2f}s")

        # ── 2. Garantir áudio local ───────────────────────────────
        audio_local = _ensure_local_audio(audio_source, safe_job_id)
        print(f"   🎵 Áudio original: {_get_duration(audio_local):.2f}s")

        # ── 3. Normalizar áudio completo e subir para R2 ──────────
        #    O Demucs precisa de uma URL pública do áudio
        full_audio_norm = _normalize_audio(audio_local, safe_job_id,
                                           suffix="full_norm")
        audio_r2_url = _upload_to_r2(
            full_audio_norm,
            f"audio/{safe_job_id}/full_audio.mp3"
        )
        if not audio_r2_url:
            return {"success": False, "error": "Falha ao publicar áudio no R2 para Demucs"}
        if not _check_url(audio_r2_url, "Áudio para Demucs"):
            return {"success": False, "error": "Áudio não acessível pelo Demucs"}

        # ── 4. DEMUCS — extrai só a voz da música ─────────────────
        vocals_url = _extract_vocals_demucs(audio_r2_url, safe_job_id)

        if vocals_url:
            # Baixa os vocals localmente para normalizar e cortar no tamanho do vídeo
            vocals_local = os.path.join(UPLOAD_DIR, f"{safe_job_id}_vocals_raw.mp3")
            ok = _download_to_local(vocals_url, vocals_local, timeout=120)
            if ok:
                vocals_norm = _normalize_audio(
                    vocals_local, safe_job_id,
                    duration_cap=video_duration,
                    suffix="vocals_norm"
                )
                vocals_r2_url = _upload_to_r2(
                    vocals_norm,
                    f"audio/{safe_job_id}/vocals.mp3"
                )
                if vocals_r2_url and _check_url(vocals_r2_url, "Vocals Demucs"):
                    print(f"   ✅ Vocals isolados prontos — usando para sync")
                    final_audio_url = vocals_r2_url
                else:
                    print(f"   ⚠️ Vocals R2 upload falhou — usando áudio completo")
                    final_audio_url = audio_r2_url
            else:
                print(f"   ⚠️ Download vocals falhou — usando áudio completo")
                final_audio_url = audio_r2_url
        else:
            # Demucs falhou: fallback gracioso para áudio completo
            # O sync ainda funciona, só fica levemente menos preciso
            print(f"   ⚠️ Demucs falhou — fallback: áudio completo para Sync Labs")
            final_audio_url = audio_r2_url

        # ── 5. Garantir URL pública do vídeo ──────────────────────
        if isinstance(face_source, str) and face_source.startswith(("http://", "https://")):
            video_url = face_source
        else:
            video_url = _upload_to_r2(
                video_local,
                f"jobs/{safe_job_id}/lipsync_input.mp4"
            )
        if not video_url:
            return {"success": False, "error": "Falha ao publicar vídeo no R2"}
        if not _check_url(video_url, "Vídeo para Sync Labs"):
            return {"success": False, "error": "Vídeo não acessível pelo Sync Labs"}

        # ── 6. SYNC LABS sync-2 — lipsync com vocals limpos ───────
        result = _run_synclabs(video_url, final_audio_url)
        if not result.get("success"):
            return {"success": False, "error": result.get("error", "Sync Labs falhou")}

        final_video_url = result["video_url"]

        # ── 7. Salvar resultado no R2 ─────────────────────────────
        local_out = os.path.join(UPLOAD_DIR, f"{safe_job_id}_lipsync.mp4")
        _download_to_local(final_video_url, local_out, timeout=600)
        r2_url = None
        if os.path.exists(local_out):
            r2_url = _upload_to_r2(local_out, f"lipsync/{safe_job_id}/lipsync.mp4")

        vocals_used = "demucs_vocals" if vocals_url else "full_audio_fallback"
        print(f"   ✅ Lipsync concluído | áudio usado: {vocals_used}")
        print(f"{'='*60}\n")

        return {
            "success":        True,
            "video_url":      r2_url or final_video_url,
            "provider_url":   final_video_url,
            "task_id":        result.get("task_id", ""),
            "provider":       "fal.ai / Demucs + Sync Labs sync-2",
            "vocals_source":  vocals_used,
            "model_endpoint": SYNCLABS_ENDPOINT,
            "model":          SYNCLABS_MODEL,
        }

    except Exception as e:
        import traceback; traceback.print_exc()
        return {"success": False, "error": str(e)}
