"""
🎬 ClipVox - Video Generation Service (Image Generation)
──────────────────────────────────────────────────────────────
Gera imagens cinematográficas usando Stability AI (SD3.5)
E faz upload pro CloudFlare R2 para armazenamento permanente

🆕 FEATURES:
- ✅ FEATURE 2: Aspect Ratio (16:9, 9:16, 1:1, 4:3)
- ✅ FEATURE 3: Resolution (720p, 1080p)
- ✅ FEATURE 4: Visual Styles (10+ estilos)
- ✅ FEATURE 5: Reference Image (image-to-image)
- ✅ FIX: Redimensiona ref image antes de enviar pra API
"""

import os
import base64
import requests
from typing import Optional
from PIL import Image  # 🆕 Para redimensionar imagem de referência
import io

from config import (
    STABILITY_API_KEY, 
    UPLOAD_DIR, 
    VISUAL_STYLES,  # 🆕 FEATURE 4
    R2_BUCKET_NAME,
    R2_PUBLIC_URL,
    get_r2_client
)


# ═══════════════════════════════════════════════════════════════════
# 🆕 ASPECT RATIO DIMENSIONS
# ═══════════════════════════════════════════════════════════════════
ASPECT_RATIO_DIMENSIONS = {
    "16:9": {
        "720p": (1280, 720),
        "1080p": (1920, 1080)
    },
    "9:16": {
        "720p": (720, 1280),
        "1080p": (1080, 1920)
    },
    "1:1": {
        "720p": (1024, 1024),
        "1080p": (1536, 1536)
    },
    "4:3": {
        "720p": (1024, 768),
        "1080p": (1536, 1152)
    }
}


# ═══════════════════════════════════════════════════════════════════
# 🆕 FIX: RESIZE REFERENCE IMAGE TO ASPECT RATIO
# ═══════════════════════════════════════════════════════════════════
def resize_image_to_aspect_ratio(
    image_path: str,
    aspect_ratio: str = "16:9",
    resolution: str = "720p"
) -> str:
    """
    🔧 FIX CRÍTICO: Redimensiona imagem de referência para o aspect ratio desejado
    
    Stability AI image-to-image NÃO permite especificar aspect_ratio no payload.
    O aspect ratio é HERDADO da imagem enviada.
    
    Solução: Redimensionar a imagem ANTES de enviar para a API.
    
    Args:
        image_path: Caminho da imagem original
        aspect_ratio: Proporção desejada (16:9, 9:16, 1:1, 4:3)
        resolution: Qualidade (720p, 1080p)
    
    Returns:
        str: Caminho da imagem redimensionada
    """
    try:
        # Obter dimensões target
        target_width, target_height = ASPECT_RATIO_DIMENSIONS[aspect_ratio][resolution]
        
        # Abrir imagem original
        img = Image.open(image_path)
        original_width, original_height = img.size
        
        print(f"🖼️ Resizing reference image:")
        print(f"   Original: {original_width}x{original_height}")
        print(f"   Target: {target_width}x{target_height} ({aspect_ratio}, {resolution})")
        
        # ─── Calcular crop para manter aspect ratio ───────────────
        # Calcula qual dimensão deve ser cropada
        target_aspect = target_width / target_height
        original_aspect = original_width / original_height
        
        if original_aspect > target_aspect:
            # Imagem é mais larga, crop nas laterais
            new_width = int(original_height * target_aspect)
            left = (original_width - new_width) // 2
            img = img.crop((left, 0, left + new_width, original_height))
        else:
            # Imagem é mais alta, crop em cima/baixo
            new_height = int(original_width / target_aspect)
            top = (original_height - new_height) // 2
            img = img.crop((0, top, original_width, top + new_height))
        
        # ─── Resize para dimensões target ─────────────────────────
        img = img.resize((target_width, target_height), Image.Resampling.LANCZOS)
        
        # ─── Salvar imagem redimensionada ─────────────────────────
        resized_path = image_path.replace(".jpeg", f"_resized_{aspect_ratio.replace(':', 'x')}_{resolution}.jpeg")
        resized_path = resized_path.replace(".jpg", f"_resized_{aspect_ratio.replace(':', 'x')}_{resolution}.jpg")
        resized_path = resized_path.replace(".png", f"_resized_{aspect_ratio.replace(':', 'x')}_{resolution}.png")
        
        img.save(resized_path, quality=95, optimize=True)
        
        print(f"✅ Resized image saved: {os.path.basename(resized_path)}")
        
        return resized_path
        
    except Exception as e:
        print(f"⚠️ Error resizing image: {e}")
        print(f"   Using original image instead")
        return image_path


# ═══════════════════════════════════════════════════════════════════
# CLOUDFLARE R2 UPLOAD
# ═══════════════════════════════════════════════════════════════════
def upload_to_r2(local_path: str, r2_key: str) -> Optional[str]:
    """
    Faz upload de um arquivo local pro CloudFlare R2
    
    Args:
        local_path: Caminho do arquivo local
        r2_key: Key no bucket R2 (ex: "jobs/abc123/scene_001.jpg")
    
    Returns:
        URL público do arquivo no R2, ou None se falhar
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


# ═══════════════════════════════════════════════════════════════════
# GENERATE SCENE IMAGE (STABILITY AI + R2)
# ═══════════════════════════════════════════════════════════════════
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
        
        # ─── Base Payload ──────────────────────────────────────
        payload = {
            "prompt": enriched_prompt,
            "output_format": "jpeg",
            "model": "sd3.5-large",
        }
        
        # 🆕 FEATURE 5: Se tem imagem de referência, redimensiona e usa image-to-image
        files = {"none": ''}
        mode = "text-to-image"
        
        if reference_image_path and os.path.exists(reference_image_path):
            print(f"🖼️ Using reference image for scene {scene_number}")
            
            # 🔧 FIX CRÍTICO: Redimensionar imagem ANTES de enviar
            resized_image_path = resize_image_to_aspect_ratio(
                reference_image_path,
                aspect_ratio,
                resolution
            )
            
            # Ler imagem redimensionada
            with open(resized_image_path, 'rb') as f:
                files = {"image": f.read()}
            
            mode = "image-to-image"
            payload["mode"] = "image-to-image"
            payload["strength"] = 0.7  # 0-1, quanto mais alto mais difere da original
            
            # ❌ NÃO enviar aspect_ratio quando mode = image-to-image
            # A Stability AI usa o aspect ratio da imagem enviada
            
        else:
            # ✅ SÓ envia aspect_ratio quando NÃO tem reference image
            payload["aspect_ratio"] = aspect_ratio  # "16:9", "9:16", "1:1", "4:3"
        
        headers = {
            "Authorization": f"Bearer {STABILITY_API_KEY}",
            "Accept": "application/json"
        }
        
        # ─── Fazer Request ────────────────────────────────────
        print(f"🎨 Generating scene {scene_number} [{aspect_ratio}, {resolution}, {style}]")
        if reference_image_path:
            print(f"   With reference image: {os.path.basename(reference_image_path)}")
            print(f"   Mode: image-to-image (aspect_ratio inherited from image)")
        else:
            print(f"   Mode: text-to-image (aspect_ratio in payload)")
        
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
            "scene_number": scene_number,  # 🔧 FIX: Incluir scene_number
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
        return _generate_placeholder_image(scene_number, prompt)


# ═══════════════════════════════════════════════════════════════════
# PLACEHOLDER IMAGE (quando API falha)
# ═══════════════════════════════════════════════════════════════════
def _generate_placeholder_image(scene_number: int, prompt: str) -> dict:
    """Gera uma imagem placeholder quando a API falha"""
    
    placeholder_text = f"Scene {scene_number}\n{prompt[:50]}..."
    
    # Criar imagem simples com PIL
    img = Image.new('RGB', (1280, 720), color=(40, 40, 50))
    
    filename = f"scene_{scene_number:03d}_placeholder.jpg"
    local_path = os.path.join(UPLOAD_DIR, filename)
    img.save(local_path)
    
    return {
        "success": False,
        "scene_number": scene_number,  # 🔧 FIX: Incluir scene_number
        "image_path": local_path,
        "image_url": f"/api/files/{filename}",
        "r2_url": None,
        "prompt_used": prompt[:100],
        "mode": "placeholder",
        "aspect_ratio": "16:9",
        "resolution": "720p"
    }


# ═══════════════════════════════════════════════════════════════════
# GENERATE SCENES BATCH (processa múltiplas scenes)
# ═══════════════════════════════════════════════════════════════════
def generate_scenes_batch(
    scenes: list,
    style: str = "realistic",
    aspect_ratio: str = "16:9",       # 🆕 FEATURE 2
    resolution: str = "720p",         # 🆕 FEATURE 3
    reference_image_path: str = None, # 🆕 FEATURE 5
    job_id: str = ""
) -> list:
    """
    Gera imagens para múltiplas scenes em batch
    
    Args:
        scenes: Lista de scenes [{scene_number, prompt, ...}]
        style: Estilo visual
        aspect_ratio: Proporção da imagem
        resolution: Qualidade
        reference_image_path: Caminho da imagem de referência
        job_id: ID do job
    
    Returns:
        Lista de dicts com resultados de cada scene
    """
    
    results = []
    successful_count = 0
    
    print(f"🎨 Generating {len(scenes)} scene images with Stability AI...")
    print(f"   Style: {style}")
    print(f"   Aspect Ratio: {aspect_ratio}")
    print(f"   Resolution: {resolution}")
    if reference_image_path:
        print(f"   Reference Image: {os.path.basename(reference_image_path)}")
    
    print("📤 Uploading to CloudFlare R2...")
    
    for scene in scenes:
        result = generate_scene_image(
            prompt=scene["prompt"],
            scene_number=scene["scene_number"],
            style=style,
            aspect_ratio=aspect_ratio,
            resolution=resolution,
            reference_image_path=reference_image_path,
            job_id=job_id
        )
        
        if result["success"]:
            successful_count += 1
        
        results.append(result)
    
    print(f"✅ Generated {successful_count}/{len(scenes)} scenes successfully")
    
    return results
