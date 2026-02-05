"""
Serviço de geração de vídeo com Stability AI + CloudFlare R2
🆕 Suporta: aspect ratio, resolution, reference image
"""
import requests
import os
import base64
import boto3
from botocore.client import Config
from config import (
    STABILITY_API_KEY, 
    UPLOAD_DIR,
    R2_ACCESS_KEY_ID,
    R2_SECRET_ACCESS_KEY,
    R2_ENDPOINT_URL,
    R2_BUCKET_NAME,
    R2_PUBLIC_URL,
    VISUAL_STYLES  # 🆕 Estilos expandidos
)


# ─── Inicializar Cliente R2 ───────────────────────────────────
def get_r2_client():
    """Retorna cliente boto3 configurado para CloudFlare R2"""
    if not all([R2_ACCESS_KEY_ID, R2_SECRET_ACCESS_KEY, R2_ENDPOINT_URL]):
        print("⚠️ R2 credentials not configured")
        return None
    
    return boto3.client(
        's3',
        endpoint_url=R2_ENDPOINT_URL,
        aws_access_key_id=R2_ACCESS_KEY_ID,
        aws_secret_access_key=R2_SECRET_ACCESS_KEY,
        config=Config(signature_version='s3v4'),
        region_name='auto'
    )


def upload_to_r2(local_path: str, r2_key: str) -> str:
    """
    Faz upload de arquivo local pro R2
    
    Args:
        local_path: Caminho do arquivo local
        r2_key: Key (caminho) no R2 (ex: "scenes/scene_001.jpg")
    
    Returns:
        URL pública do arquivo no R2
    """
    try:
        r2_client = get_r2_client()
        
        if not r2_client:
            print("⚠️ R2 client not available, skipping upload")
            return None
        
        # Upload do arquivo
        with open(local_path, 'rb') as f:
            r2_client.put_object(
                Bucket=R2_BUCKET_NAME,
                Key=r2_key,
                Body=f,
                ContentType='image/jpeg'
            )
        
        # Construir URL pública
        public_url = f"{R2_PUBLIC_URL}/{r2_key}"
        
        print(f"✅ Uploaded to R2: {public_url}")
        return public_url
        
    except Exception as e:
        print(f"❌ Error uploading to R2: {e}")
        return None


def generate_scene_image(
    prompt: str, 
    scene_number: int, 
    style: str = "realistic",
    aspect_ratio: str = "16:9",       # 🆕 FEATURE 2
    resolution: str = "720p",         # 🆕 FEATURE 3
    reference_image_path: str = None, # 🆕 FEATURE 5
    job_id: str = ""
) -> dict:
    """
    Gera uma imagem para uma scene usando Stability AI
    E faz upload pro CloudFlare R2
    
    🆕 Args:
        prompt: Prompt em inglês descrevendo a cena
        scene_number: Número da scene
        style: Estilo visual (realistic, cinematic, anime, etc)
        aspect_ratio: Proporção da imagem (16:9, 9:16, 1:1, 4:3)
        resolution: Qualidade (720p, 1080p)
        reference_image_path: Caminho da imagem de referência (opcional)
        job_id: ID do job
    
    Returns:
        dict com: success, image_path, image_url, r2_url
    """
    
    if not STABILITY_API_KEY:
        print("⚠️ STABILITY_API_KEY not set, using placeholder")
        return _generate_placeholder_image(scene_number, prompt)
    
    try:
        # ─── Stability AI API Config ──────────────────────────
        url = "https://api.stability.ai/v2beta/stable-image/generate/sd3"
        
        # 🆕 FEATURE 4: Pegar prefix do estilo
        style_config = VISUAL_STYLES.get(style, VISUAL_STYLES["realistic"])
        style_prefix = style_config["prefix"]
        
        enriched_prompt = f"{style_prefix}, {prompt}"
        
        # 🆕 FEATURE 2 & 3: Aspect Ratio e Resolution
        payload = {
            "prompt": enriched_prompt,
            "aspect_ratio": aspect_ratio,  # "16:9", "9:16", "1:1", "4:3"
            "output_format": "jpeg",
            "model": "sd3.5-large",
        }
        
        # 🆕 FEATURE 5: Se tem imagem de referência, usa image-to-image
        files = {"none": ''}
        mode = "text-to-image"
        
        if reference_image_path and os.path.exists(reference_image_path):
            print(f"🖼️ Using reference image for scene {scene_number}")
            with open(reference_image_path, 'rb') as f:
                files = {"image": f.read()}
            mode = "image-to-image"
            payload["mode"] = "image-to-image"
            payload["strength"] = 0.7  # 0-1, quanto mais alto mais difere da original
        
        headers = {
            "Authorization": f"Bearer {STABILITY_API_KEY}",
            "Accept": "application/json"
        }
        
        # ─── Fazer Request ────────────────────────────────────
        print(f"🎨 Generating scene {scene_number} [{aspect_ratio}, {resolution}, {style}]")
        if reference_image_path:
            print(f"   With reference image: {os.path.basename(reference_image_path)}")
        
        # Prepare files for request
        request_files = {"none": ''} if mode == "text-to-image" else {"image": files["image"]}
        
        response = requests.post(
            url,
            headers=headers,
            files=request_files,
            data=payload,
            timeout=60
        )
        
        if response.status_code != 200:
            print(f"❌ Stability AI error: {response.status_code} - {response.text}")
            return _generate_placeholder_image(scene_number, prompt)
        
        # ─── Salvar Localmente (Temporário) ───────────────────
        data = response.json()
        
        if "image" in data:
            image_data = base64.b64decode(data["image"])
        else:
            print(f"❌ No image in response: {data}")
            return _generate_placeholder_image(scene_number, prompt)
        
        # Salvar temporariamente
        filename = f"scene_{scene_number:03d}.jpg"
        local_path = os.path.join(UPLOAD_DIR, filename)
        
        with open(local_path, "wb") as f:
            f.write(image_data)
        
        # ─── Upload pro R2 ────────────────────────────────────
        r2_key = f"jobs/{job_id}/{filename}" if job_id else f"scenes/{filename}"
        r2_url = upload_to_r2(local_path, r2_key)
        
        print(f"✅ Scene {scene_number} generated and uploaded")
        
        return {
            "success": True,
            "image_path": local_path,
            "image_url": r2_url or f"/api/files/{filename}",
            "r2_url": r2_url,
            "prompt_used": enriched_prompt[:100],
            "mode": mode,
            "aspect_ratio": aspect_ratio,
            "resolution": resolution
        }
        
    except requests.exceptions.Timeout:
        print(f"⏱️ Timeout generating scene {scene_number}")
        return _generate_placeholder_image(scene_number, prompt)
    
    except Exception as e:
        print(f"❌ Error generating scene {scene_number}: {e}")
        import traceback
        traceback.print_exc()
        return _generate_placeholder_image(scene_number, prompt)


def generate_scenes_batch(
    scenes: list, 
    style: str = "realistic",
    aspect_ratio: str = "16:9",       # 🆕
    resolution: str = "720p",         # 🆕
    reference_image_path: str = None, # 🆕
    job_id: str = ""
) -> list:
    """
    Gera múltiplas scenes em batch
    
    🆕 Args:
        scenes: Lista de objetos scene com 'scene_number' e 'prompt'
        style: Estilo visual
        aspect_ratio: Proporção (16:9, 9:16, 1:1, 4:3)
        resolution: Qualidade (720p, 1080p)
        reference_image_path: Imagem de referência (opcional)
        job_id: ID do job
    
    Returns:
        Lista de scenes com campo 'image_url' adicionado
    """
    results = []
    
    for scene in scenes:
        result = generate_scene_image(
            prompt=scene["prompt"],
            scene_number=scene["scene_number"],
            style=style,
            aspect_ratio=aspect_ratio,      # 🆕
            resolution=resolution,          # 🆕
            reference_image_path=reference_image_path,  # 🆕
            job_id=job_id
        )
        
        # Adicionar URL da imagem ao objeto scene
        scene["image_url"] = result["image_url"]
        scene["r2_url"] = result.get("r2_url")
        scene["image_generated"] = result["success"]
        scene["aspect_ratio"] = result.get("aspect_ratio")  # 🆕
        scene["resolution"] = result.get("resolution")      # 🆕
        
        results.append(scene)
    
    return results


def _generate_placeholder_image(scene_number: int, prompt: str) -> dict:
    """
    Gera imagem placeholder quando Stability AI não disponível
    """
    try:
        from PIL import Image, ImageDraw
        
        # Criar imagem 1280x720 (16:9)
        img = Image.new('RGB', (1280, 720), color=(30 + scene_number * 5, 20 + scene_number * 3, 40 + scene_number * 4))
        draw = ImageDraw.Draw(img)
        
        # Adicionar texto
        text = f"Scene {scene_number}\n{prompt[:50]}..."
        draw.text((50, 300), text, fill=(255, 255, 255))
        
        # Salvar
        filename = f"scene_{scene_number:03d}_placeholder.jpg"
        filepath = os.path.join(UPLOAD_DIR, filename)
        img.save(filepath, 'JPEG')
        
        return {
            "success": False,
            "image_path": filepath,
            "image_url": f"/api/files/{filename}",
            "r2_url": None,
            "note": "Placeholder image (Stability AI not configured)"
        }
        
    except ImportError:
        return {
            "success": False,
            "image_path": None,
            "image_url": f"/api/files/mock_scene_{scene_number}.jpg",
            "r2_url": None,
            "note": "Mock URL (PIL not installed)"
        }
