"""
🎬 ClipVox - Merge Service
Concatena clipes de vídeo e adiciona o áudio original
"""

import os
import subprocess
import tempfile
import requests
import uuid
from typing import List, Optional

def merge_clips_with_audio(
    video_urls: List[str],
    audio_path: str,
    job_id: str,
    r2_client=None,
    r2_bucket_name: str = None,
    r2_public_url: str = None
) -> dict:
    """
    Baixa os clipes, concatena e adiciona o áudio original.
    Retorna dict com success, output_url, error.
    """
    tmpdir = tempfile.mkdtemp()
    
    try:
        # 1. Baixar todos os clipes
        clip_paths = []
        for i, url in enumerate(video_urls):
            print(f"   📥 Baixando clipe {i+1}/{len(video_urls)}: {url[:60]}")
            r = requests.get(url, timeout=60)
            if r.status_code != 200:
                print(f"   ⚠️ Falha ao baixar clipe {i+1} (HTTP {r.status_code})")
                continue
            clip_path = os.path.join(tmpdir, f"clip_{i:03d}.mp4")
            with open(clip_path, "wb") as f:
                f.write(r.content)
            clip_paths.append(clip_path)
            print(f"   ✅ Clipe {i+1} baixado ({len(r.content)//1024}KB)")

        if not clip_paths:
            return {"success": False, "error": "Nenhum clipe pôde ser baixado"}

        # 2. Criar arquivo de concatenação
        concat_file = os.path.join(tmpdir, "concat.txt")
        with open(concat_file, "w") as f:
            for path in clip_paths:
                f.write(f"file '{path}'\n")

        # 3. Concatenar vídeos
        merged_video = os.path.join(tmpdir, "merged_video.mp4")
        print(f"   🎬 Concatenando {len(clip_paths)} clipes...")
        
        result = subprocess.run([
            "ffmpeg", "-y",
            "-f", "concat",
            "-safe", "0",
            "-i", concat_file,
            "-c", "copy",
            merged_video
        ], capture_output=True, text=True, timeout=120)

        if result.returncode != 0:
            print(f"   ❌ ffmpeg concat erro: {result.stderr[-500:]}")
            return {"success": False, "error": f"Erro ao concatenar: {result.stderr[-200:]}"}

        print(f"   ✅ Vídeos concatenados")

        # 4. Adicionar áudio
        output_path = os.path.join(tmpdir, f"final_{job_id}.mp4")
        print(f"   🎵 Adicionando áudio: {audio_path}")

        result = subprocess.run([
            "ffmpeg", "-y",
            "-i", merged_video,
            "-i", audio_path,
            "-map", "0:v:0",
            "-map", "1:a:0",
            "-c:v", "copy",
            "-c:a", "aac",
            "-b:a", "192k",
            "-shortest",
            output_path
        ], capture_output=True, text=True, timeout=180)

        if result.returncode != 0:
            print(f"   ❌ ffmpeg audio erro: {result.stderr[-500:]}")
            # Tenta sem áudio se falhar
            output_path = merged_video
            print(f"   ⚠️ Usando vídeo sem áudio")

        print(f"   ✅ Merge finalizado: {os.path.getsize(output_path)//1024}KB")

        # 5. Upload para R2
        if r2_client and r2_bucket_name and r2_public_url:
            r2_key = f"jobs/{job_id}/final_video.mp4"
            print(f"   📤 Enviando para R2: {r2_key}")
            
            with open(output_path, "rb") as f:
                r2_client.put_object(
                    Bucket=r2_bucket_name,
                    Key=r2_key,
                    Body=f.read(),
                    ContentType="video/mp4"
                )
            
            public_url = f"{r2_public_url}/{r2_key}"
            print(f"   ✅ Upload concluído: {public_url}")
            return {"success": True, "output_url": public_url, "r2_key": r2_key}
        else:
            # Retorna o arquivo local (fallback)
            print(f"   ⚠️ R2 não configurado — retornando path local")
            return {"success": True, "output_url": None, "local_path": output_path}

    except subprocess.TimeoutExpired:
        return {"success": False, "error": "Timeout no processo de merge"}
    except Exception as e:
        import traceback
        traceback.print_exc()
        return {"success": False, "error": str(e)}
    finally:
        # Limpar arquivos temporários (exceto output se não foi para R2)
        for f in os.listdir(tmpdir):
            try:
                fp = os.path.join(tmpdir, f)
                if fp != output_path or r2_client:
                    os.remove(fp)
            except:
                pass
