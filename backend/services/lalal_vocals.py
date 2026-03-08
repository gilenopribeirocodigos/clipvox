"""
🎵 ClipVox - LALAL.AI Vocal Extraction Service
Extrai apenas a voz da música, removendo instrumentos.
Isso melhora drasticamente a qualidade do lip sync.

CORREÇÃO: LALAL.AI exige upload raw binary com Content-Disposition como
header HTTP — NÃO multipart/form-data. Erro anterior:
"Required argument content-disposition not found"
"""

import os
import time
import requests
from typing import Optional
from config import UPLOAD_DIR

LALAL_API_KEY  = os.getenv("LALAL_API_KEY", "")
LALAL_API_BASE = "https://www.lalal.ai/api"


def extract_vocals(audio_path: str, job_id: str = "") -> Optional[str]:
    """
    Envia o áudio para o LALAL.AI e retorna o caminho do WAV só com vocals.
    Retorna: caminho local do arquivo de vocals, ou None se falhar.
    """
    if not LALAL_API_KEY:
        print("❌ LALAL_API_KEY não configurada")
        return None

    print(f"🎵 LALAL.AI — extraindo vocals de: {os.path.basename(audio_path)}")

    # ── 1. Upload do arquivo ──────────────────────────────────────────────────
    file_id = _upload_file(audio_path)
    if not file_id:
        return None

    # ── 2. Iniciar separação (vocals + instrumental) ──────────────────────────
    task_id = _start_split(file_id)
    if not task_id:
        return None

    # ── 3. Aguardar processamento ─────────────────────────────────────────────
    vocal_url = _poll_result(task_id)
    if not vocal_url:
        return None

    # ── 4. Baixar o arquivo de vocals ─────────────────────────────────────────
    vocal_path = _download_vocals(vocal_url, job_id)
    return vocal_path


def _upload_file(audio_path: str) -> Optional[str]:
    """
    Faz upload do áudio para o LALAL.AI. Retorna o file_id.

    ✅ CORREÇÃO: LALAL.AI usa upload raw binary (não multipart/form-data).
    O Content-Disposition deve ser um header HTTP normal, não um header
    de parte multipart. O código anterior usava requests.files={} o que
    gerava multipart — a API rejeitava com "content-disposition not found".
    """
    try:
        print(f"   📤 Enviando para LALAL.AI (raw binary)...")
        filename = os.path.basename(audio_path)
        ext      = filename.rsplit(".", 1)[-1].lower()
        ct_map   = {
            "mp3": "audio/mpeg", "wav": "audio/wav",
            "ogg": "audio/ogg",  "m4a": "audio/mp4",
            "aac": "audio/aac",  "flac": "audio/flac",
        }
        content_type = ct_map.get(ext, "audio/mpeg")

        with open(audio_path, "rb") as f:
            file_bytes = f.read()

        resp = requests.post(
            f"{LALAL_API_BASE}/upload/",
            headers={
                "Authorization":     f"license {LALAL_API_KEY}",
                # ✅ Content-Disposition como header HTTP (não multipart)
                "Content-Disposition": f'attachment; filename="{filename}"',
                "Content-Type":      content_type,
            },
            data=file_bytes,   # raw binary — NÃO files={}
            timeout=120,
        )
        print(f"   📥 Upload HTTP {resp.status_code}: {resp.text[:200]}")
        data = resp.json()
        if resp.status_code != 200 or data.get("status") == "error":
            print(f"   ❌ Upload falhou: {data.get('error', 'erro desconhecido')}")
            return None
        file_id = data.get("id")
        print(f"   ✅ Upload OK — file_id: {file_id}")
        return file_id
    except Exception as e:
        print(f"   ❌ Erro upload LALAL.AI: {e}")
        return None


def _start_split(file_id: str) -> Optional[str]:
    """Inicia a separação vocal. Retorna o task_id."""
    try:
        print(f"   🔀 Iniciando separação vocal...")
        resp = requests.post(
            f"{LALAL_API_BASE}/split/",
            headers={
                "Authorization": f"license {LALAL_API_KEY}",
                "Content-Type":  "application/json",
            },
            json={
                "id":       file_id,
                "stem":     "vocals",    # extrai só vocals
                "splitter": "phoenix",   # modelo de qualidade
            },
            timeout=30,
        )
        print(f"   📥 Split HTTP {resp.status_code}: {resp.text[:200]}")
        data = resp.json()
        if resp.status_code != 200 or data.get("status") == "error":
            print(f"   ❌ Split falhou: {data.get('error', 'erro desconhecido')}")
            return None
        task_id = data.get("task_id") or file_id
        print(f"   ✅ Separação iniciada — task_id: {task_id}")
        return task_id
    except Exception as e:
        print(f"   ❌ Erro split LALAL.AI: {e}")
        return None


def _poll_result(task_id: str, timeout: int = 300) -> Optional[str]:
    """Aguarda o processamento e retorna a URL do arquivo de vocals."""
    print(f"   ⏳ Aguardando processamento LALAL.AI...")
    for elapsed in range(10, timeout + 1, 10):
        time.sleep(10)
        try:
            resp = requests.get(
                f"{LALAL_API_BASE}/check/",
                headers={"Authorization": f"license {LALAL_API_KEY}"},
                params={"id": task_id},
                timeout=15,
            )
            data   = resp.json()
            status = data.get("status", "")
            print(f"   ⏳ Status: {status} ({elapsed}s)")

            if status == "success":
                split     = data.get("split_results", {})
                vocal_url = (
                    split.get("vocals_url") or
                    split.get("stem_url")   or
                    data.get("vocal_url")   or
                    data.get("vocals_url")
                )
                if vocal_url:
                    print(f"   ✅ Vocals prontos: {vocal_url[:80]}")
                    return vocal_url
                print(f"   ❌ URL de vocals não encontrada: {data}")
                return None

            elif status == "error":
                print(f"   ❌ LALAL.AI erro: {data.get('error')}")
                return None

        except Exception as e:
            print(f"   ⚠️ Polling erro: {e}")

    print(f"   ❌ Timeout ({timeout}s) aguardando LALAL.AI")
    return None


def _download_vocals(vocal_url: str, job_id: str) -> Optional[str]:
    """Baixa o arquivo de vocals e salva localmente."""
    try:
        print(f"   📥 Baixando vocals...")
        resp = requests.get(vocal_url, timeout=120, stream=True)
        if resp.status_code != 200:
            print(f"   ❌ Download falhou: HTTP {resp.status_code}")
            return None
        filename   = f"{job_id}_vocals.wav" if job_id else f"vocals_{int(time.time())}.wav"
        local_path = os.path.join(UPLOAD_DIR, filename)
        with open(local_path, "wb") as f:
            for chunk in resp.iter_content(chunk_size=8192):
                f.write(chunk)
        print(f"   ✅ Vocals salvo: {local_path}")
        return local_path
    except Exception as e:
        print(f"   ❌ Erro download vocals: {e}")
        return None
