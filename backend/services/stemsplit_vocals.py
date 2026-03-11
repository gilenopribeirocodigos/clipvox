"""
🎵 ClipVox - StemSplit.io Vocal Extraction Service
Substitui o LALAL.AI — extrai apenas a voz da música para lip sync.

Fluxo:
  1. POST /upload         → obtém presigned URL + uploadKey
  2. PUT <presigned_url>  → envia o arquivo de áudio
  3. POST /jobs           → cria job de separação (outputType: VOCALS)
  4. GET /jobs/:id        → polling até COMPLETED
  5. Download vocals URL  → salva localmente
"""

import os
import time
import requests
from typing import Optional
from config import UPLOAD_DIR

STEMSPLIT_API_KEY  = os.getenv("STEMSPLIT_API_KEY", "")
STEMSPLIT_API_BASE = "https://stemsplit.io/api/v1"


def extract_vocals(audio_path: str, job_id: str = "") -> Optional[str]:
    """
    Envia o áudio para o StemSplit.io e retorna o caminho local do MP3 só com vocals.
    Retorna: caminho local do arquivo de vocals, ou None se falhar.
    """
    if not STEMSPLIT_API_KEY:
        print("❌ STEMSPLIT_API_KEY não configurada")
        return None

    print(f"🎵 StemSplit.io — extraindo vocals de: {os.path.basename(audio_path)}")

    # 1. Obtém URL de upload
    upload_key, presigned_url = _get_upload_url(audio_path)
    if not upload_key or not presigned_url:
        return None

    # 2. Faz upload do arquivo
    if not _upload_file(audio_path, presigned_url):
        return None

    # 3. Cria job de separação
    stem_job_id = _create_job(upload_key)
    if not stem_job_id:
        return None

    # 4. Aguarda conclusão
    vocal_url = _poll_result(stem_job_id)
    if not vocal_url:
        return None

    # 5. Baixa e salva localmente
    return _download_vocals(vocal_url, job_id)


def _get_upload_url(audio_path: str):
    """Obtém presigned URL para upload do arquivo."""
    try:
        filename = os.path.basename(audio_path)
        ext = filename.rsplit(".", 1)[-1].lower()
        ct_map = {
            "mp3": "audio/mpeg", "wav": "audio/wav",
            "ogg": "audio/ogg",  "m4a": "audio/mp4",
            "aac": "audio/aac",  "flac": "audio/flac",
        }
        content_type = ct_map.get(ext, "audio/mpeg")

        print(f"   📋 Obtendo URL de upload...")
        resp = requests.post(
            f"{STEMSPLIT_API_BASE}/upload",
            headers={
                "Authorization": f"Bearer {STEMSPLIT_API_KEY}",
                "Content-Type":  "application/json",
            },
            json={
                "filename":    filename,
                "contentType": content_type,
            },
            timeout=30,
        )
        print(f"   📥 Upload URL HTTP {resp.status_code}: {resp.text[:200]}")

        if resp.status_code != 200:
            print(f"   ❌ Falha ao obter URL de upload: {resp.text[:200]}")
            return None, None

        data        = resp.json()
        upload_url  = data.get("uploadUrl")
        upload_key  = data.get("uploadKey")

        if not upload_url or not upload_key:
            print(f"   ❌ Resposta inválida: {data}")
            return None, None

        print(f"   ✅ Upload URL obtida — key: {upload_key}")
        return upload_key, upload_url

    except Exception as e:
        print(f"   ❌ Erro ao obter URL de upload: {e}")
        return None, None


def _upload_file(audio_path: str, presigned_url: str) -> bool:
    """Envia o arquivo de áudio para o presigned URL via PUT."""
    try:
        filename = os.path.basename(audio_path)
        ext      = filename.rsplit(".", 1)[-1].lower()
        ct_map   = {
            "mp3": "audio/mpeg", "wav": "audio/wav",
            "ogg": "audio/ogg",  "m4a": "audio/mp4",
            "aac": "audio/aac",  "flac": "audio/flac",
        }
        content_type = ct_map.get(ext, "audio/mpeg")

        print(f"   📤 Enviando arquivo para StemSplit...")
        with open(audio_path, "rb") as f:
            resp = requests.put(
                presigned_url,
                headers={"Content-Type": content_type},
                data=f,
                timeout=120,
            )

        if resp.status_code not in (200, 204):
            print(f"   ❌ Upload falhou: HTTP {resp.status_code} — {resp.text[:200]}")
            return False

        print(f"   ✅ Arquivo enviado com sucesso")
        return True

    except Exception as e:
        print(f"   ❌ Erro no upload do arquivo: {e}")
        return False


def _create_job(upload_key: str) -> Optional[str]:
    """Cria o job de separação vocal no StemSplit."""
    try:
        print(f"   🔧 Criando job de separação vocal...")
        resp = requests.post(
            f"{STEMSPLIT_API_BASE}/jobs",
            headers={
                "Authorization": f"Bearer {STEMSPLIT_API_KEY}",
                "Content-Type":  "application/json",
            },
            json={
                "uploadKey":    upload_key,
                "outputType":   "VOCALS",   # só vocals — economiza créditos
                "quality":      "BEST",
                "outputFormat": "MP3",
            },
            timeout=30,
        )
        print(f"   📥 Job HTTP {resp.status_code}: {resp.text[:200]}")

        if resp.status_code != 200:
            print(f"   ❌ Falha ao criar job: {resp.text[:200]}")
            return None

        data       = resp.json()
        stem_job_id = data.get("id")

        if not stem_job_id:
            print(f"   ❌ ID do job não encontrado: {data}")
            return None

        credits = data.get("creditsRequired", "?")
        print(f"   ✅ Job criado — id: {stem_job_id} | créditos: {credits}s")
        return stem_job_id

    except Exception as e:
        print(f"   ❌ Erro ao criar job: {e}")
        return None


def _poll_result(stem_job_id: str, timeout: int = 300) -> Optional[str]:
    """Aguarda o processamento e retorna a URL do arquivo de vocals."""
    print(f"   ⏳ Aguardando processamento StemSplit...")

    for elapsed in range(10, timeout + 1, 10):
        time.sleep(10)
        try:
            resp = requests.get(
                f"{STEMSPLIT_API_BASE}/jobs/{stem_job_id}",
                headers={"Authorization": f"Bearer {STEMSPLIT_API_KEY}"},
                timeout=15,
            )
            data   = resp.json()
            status = data.get("status", "")
            progress = data.get("progress", 0)
            print(f"   ⏳ Status: {status} ({progress}%) — {elapsed}s")

            if status == "COMPLETED":
                outputs   = data.get("outputs", {})
                vocal_url = outputs.get("vocals", {}).get("url")
                if vocal_url:
                    print(f"   ✅ Vocals prontos: {vocal_url[:80]}")
                    return vocal_url
                print(f"   ❌ URL de vocals não encontrada: {outputs}")
                return None

            elif status == "FAILED":
                print(f"   ❌ StemSplit job falhou: {data}")
                return None

            elif status == "EXPIRED":
                print(f"   ❌ Job expirado")
                return None

        except Exception as e:
            print(f"   ⚠️ Polling erro: {e}")

    print(f"   ❌ Timeout ({timeout}s) aguardando StemSplit")
    return None


def _download_vocals(vocal_url: str, job_id: str) -> Optional[str]:
    """Baixa o arquivo de vocals e salva localmente."""
    try:
        print(f"   📥 Baixando vocals...")
        resp = requests.get(vocal_url, timeout=120, stream=True)
        if resp.status_code != 200:
            print(f"   ❌ Download falhou: HTTP {resp.status_code}")
            return None

        filename   = f"{job_id}_vocals.mp3" if job_id else f"vocals_{int(time.time())}.mp3"
        local_path = os.path.join(UPLOAD_DIR, filename)

        with open(local_path, "wb") as f:
            for chunk in resp.iter_content(chunk_size=8192):
                f.write(chunk)

        print(f"   ✅ Vocals salvo: {local_path}")
        return local_path

    except Exception as e:
        print(f"   ❌ Erro download vocals: {e}")
        return None
