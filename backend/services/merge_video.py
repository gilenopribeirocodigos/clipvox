"""
🎬 ClipVox - Merge Service
Concatena clipes de vídeo e adiciona o áudio original.
Faz upload para R2 — inicializa o client diretamente das env vars.
"""

import os
import subprocess
import tempfile
import requests
from typing import List, Optional

# ── Constantes de env vars (mesmas usadas pelo serviço de imagens) ──────────
R2_ACCOUNT_ID  = os.getenv("CLOUDFLARE_ACCOUNT_ID", "")
R2_ACCESS_KEY  = os.getenv("CLOUDFLARE_R2_ACCESS_KEY", "")
R2_SECRET_KEY  = os.getenv("CLOUDFLARE_R2_SECRET_KEY", "")
R2_BUCKET      = os.getenv("CLOUDFLARE_R2_BUCKET", "clipvox-scenes")
R2_PUBLIC_URL  = os.getenv("R2_PUBLIC_URL", "https://pub-d360cea000634ea6a69c5cb5cae8465a.r2.dev")

# Diretório para manter o arquivo final acessível via download endpoint
MERGE_OUTPUT_DIR = os.getenv("MERGE_OUTPUT_DIR", "/tmp/clipvox_merges")
os.makedirs(MERGE_OUTPUT_DIR, exist_ok=True)


def _get_r2_client():
    """Inicializa e retorna o cliente boto3 para Cloudflare R2."""
    if not R2_ACCESS_KEY or not R2_SECRET_KEY or not R2_ACCOUNT_ID:
        return None
    try:
        import boto3
        client = boto3.client(
            "s3",
            endpoint_url=f"https://{R2_ACCOUNT_ID}.r2.cloudflarestorage.com",
            aws_access_key_id=R2_ACCESS_KEY,
            aws_secret_access_key=R2_SECRET_KEY,
            region_name="auto"
        )
        return client
    except Exception as e:
        print(f"   ⚠️ Erro ao criar R2 client: {e}")
        return None


def merge_clips_with_audio(
    video_urls: List[str],
    audio_path: str,
    job_id: str,
    # Parâmetros opcionais mantidos por compatibilidade (ignorados — usa env vars)
    r2_client=None,
    r2_bucket_name: str = None,
    r2_public_url: str = None
) -> dict:
    """
    Baixa os clipes, concatena e adiciona o áudio original.
    Tenta upload para R2. Se falhar, salva localmente e retorna path para download.
    """
    tmpdir = tempfile.mkdtemp()

    try:
        # ── 1. Baixar todos os clipes ─────────────────────────────────────────
        clip_paths = []
        for i, url in enumerate(video_urls):
            print(f"   📥 Baixando clipe {i+1}/{len(video_urls)}: {url[:60]}")
            try:
                r = requests.get(url, timeout=120)
                if r.status_code != 200:
                    print(f"   ⚠️ Falha ao baixar clipe {i+1} (HTTP {r.status_code})")
                    continue
                clip_path = os.path.join(tmpdir, f"clip_{i:03d}.mp4")
                with open(clip_path, "wb") as f:
                    f.write(r.content)
                clip_paths.append(clip_path)
                print(f"   ✅ Clipe {i+1} baixado ({len(r.content)//1024}KB)")
            except Exception as e:
                print(f"   ⚠️ Erro ao baixar clipe {i+1}: {e}")

        if not clip_paths:
            return {"success": False, "error": "Nenhum clipe pôde ser baixado"}

        # ── 2. Arquivo de concatenação ────────────────────────────────────────
        concat_file = os.path.join(tmpdir, "concat.txt")
        with open(concat_file, "w") as f:
            for path in clip_paths:
                f.write(f"file '{path}'\n")

        # ── 3. Concatenar vídeos ──────────────────────────────────────────────
        merged_video = os.path.join(tmpdir, "merged_video.mp4")
        print(f"   🎬 Concatenando {len(clip_paths)} clipes...")

        result = subprocess.run([
            "ffmpeg", "-y",
            "-f", "concat", "-safe", "0",
            "-i", concat_file,
            "-c", "copy",
            merged_video
        ], capture_output=True, text=True, timeout=180)

        if result.returncode != 0:
            print(f"   ❌ ffmpeg concat erro: {result.stderr[-500:]}")
            return {"success": False, "error": f"Erro ao concatenar: {result.stderr[-200:]}"}

        print(f"   ✅ Vídeos concatenados")

        # ── 4. Adicionar áudio ────────────────────────────────────────────────
        output_path = os.path.join(tmpdir, f"final_{job_id}.mp4")
        print(f"   🎵 Adicionando áudio: {audio_path}")

        if audio_path and os.path.exists(audio_path):
            result = subprocess.run([
                "ffmpeg", "-y",
                "-i", merged_video,
                "-i", audio_path,
                "-map", "0:v:0",
                "-map", "1:a:0",
                "-c:v", "copy",
                "-c:a", "aac", "-b:a", "192k",
                "-shortest",
                output_path
            ], capture_output=True, text=True, timeout=300)

            if result.returncode != 0:
                print(f"   ⚠️ ffmpeg audio falhou — usando sem áudio: {result.stderr[-200:]}")
                output_path = merged_video
            else:
                print(f"   ✅ Áudio adicionado")
        else:
            print(f"   ⚠️ Arquivo de áudio não encontrado — usando sem áudio")
            output_path = merged_video

        file_size = os.path.getsize(output_path)
        print(f"   ✅ Merge finalizado: {file_size//1024}KB")

        # ── 5. Tentar upload para R2 ──────────────────────────────────────────
        client = _get_r2_client()
        if client:
            r2_key = f"jobs/{job_id}/final_video.mp4"
            print(f"   📤 Enviando para R2: {r2_key}")
            try:
                with open(output_path, "rb") as f:
                    client.put_object(
                        Bucket=R2_BUCKET,
                        Key=r2_key,
                        Body=f.read(),
                        ContentType="video/mp4"
                    )
                public_url = f"{R2_PUBLIC_URL}/{r2_key}"
                print(f"   ✅ Upload R2 concluído: {public_url}")
                return {"success": True, "output_url": public_url, "r2_key": r2_key}
            except Exception as e:
                print(f"   ⚠️ Upload R2 falhou: {e} — usando fallback local")
        else:
            print(f"   ⚠️ R2 não configurado — usando fallback local")

        # ── 6. Fallback: salvar em diretório permanente para download ─────────
        local_filename = f"final_{job_id}.mp4"
        local_path     = os.path.join(MERGE_OUTPUT_DIR, local_filename)
        import shutil
        shutil.copy2(output_path, local_path)
        print(f"   💾 Arquivo salvo localmente: {local_path}")

        # Retorna um path relativo que o endpoint /download/{job_id} usará
        return {
            "success":    True,
            "output_url": None,
            "local_path": local_path,
            "filename":   local_filename
        }

    except subprocess.TimeoutExpired:
        return {"success": False, "error": "Timeout no processo de merge"}
    except Exception as e:
        import traceback
        traceback.print_exc()
        return {"success": False, "error": str(e)}
    finally:
        # Limpar arquivos temporários do tmpdir
        import shutil
        try:
            shutil.rmtree(tmpdir, ignore_errors=True)
        except Exception:
            pass
