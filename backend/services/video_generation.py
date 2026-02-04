"""
Serviço de geração de vídeo com Stability AI
Gera imagens a partir dos prompts das scenes
"""
import requests
import os
import base64
from config import STABILITY_API_KEY, UPLOAD_DIR


def generate_scene_image(prompt: str, scene_number: int, style: str = "realistic") -> dict:
    """
    Gera uma imagem para uma scene usando Stability AI
    
    Args:
        prompt: Prompt em inglês descrevendo a cena
        scene_number: Número da scene (pra salvar o arquivo)
        style: Estilo visual (realistic, cinematic, animated, retro)
    
    Returns:
        dict com: success, image_path, image_url
    """
    
    if not STABILITY_API_KEY:
        print("⚠️ STABILITY_API_KEY not set, using placeholder")
        return _generate_placeholder_image(scene_number, prompt)
    
    try:
        # ─── Stability AI API Config ──────────────────────────
        # Usando Stable Diffusion 3.5 (melhor custo-benefício)
        url = "https://api.stability.ai/v2beta/stable-image/generate/sd3"
        
        # Style-specific prefixes
        style_prefixes = {
            "realistic": "photorealistic, cinematic photography, 8K HDR, professional camera, film grain, natural lighting, high detail",
            "cinematic": "cinematic masterpiece, anamorphic lens, epic composition, dramatic lighting, color grading, film still, Blade Runner aesthetic",
            "animated": "3D animation style, Pixar quality, vibrant colors, expressive, detailed render, studio ghibli influence",
            "retro": "retro 1980s aesthetic, VHS style, synthwave colors, vintage film grain, neon lights, nostalgic"
        }
        
        # Enriquecer o prompt com o style
        enriched_prompt = f"{style_prefixes.get(style, style_prefixes['realistic'])}, {prompt}"
        
        # Aspect ratio 16:9 (ideal pra vídeo)
        # Output format: jpeg (mais rápido que png)
        payload = {
            "prompt": enriched_prompt,
            "aspect_ratio": "16:9",
            "output_format": "jpeg",
            "model": "sd3.5-large",  # Melhor modelo atual
            "mode": "text-to-image"
        }
        
        headers = {
            "Authorization": f"Bearer {STABILITY_API_KEY}",
            "Accept": "application/json"
        }
        
        # ─── Fazer Request ────────────────────────────────────
        print(f"🎨 Generating scene {scene_number} with Stability AI...")
        
        response = requests.post(
            url,
            headers=headers,
            files={"none": ''},
            data=payload,
            timeout=60  # 60s timeout
        )
        
        if response.status_code != 200:
            print(f"❌ Stability AI error: {response.status_code} - {response.text}")
            return _generate_placeholder_image(scene_number, prompt)
        
        # ─── Salvar Imagem ────────────────────────────────────
        data = response.json()
        
        # A API retorna base64 da imagem
        if "image" in data:
            image_data = base64.b64decode(data["image"])
        else:
            print(f"❌ No image in response: {data}")
            return _generate_placeholder_image(scene_number, prompt)
        
        # Salvar arquivo
        filename = f"scene_{scene_number:03d}.jpg"
        filepath = os.path.join(UPLOAD_DIR, filename)
        
        with open(filepath, "wb") as f:
            f.write(image_data)
        
        print(f"✅ Scene {scene_number} generated: {filepath}")
        
        return {
            "success": True,
            "image_path": filepath,
            "image_url": f"/api/files/{filename}",
            "prompt_used": enriched_prompt[:100]  # primeiros 100 chars
        }
        
    except requests.exceptions.Timeout:
        print(f"⏱️ Timeout generating scene {scene_number}")
        return _generate_placeholder_image(scene_number, prompt)
    
    except Exception as e:
        print(f"❌ Error generating scene {scene_number}: {e}")
        return _generate_placeholder_image(scene_number, prompt)


def generate_scenes_batch(scenes: list, style: str = "realistic", max_parallel: int = 3) -> list:
    """
    Gera múltiplas scenes em batch
    
    Args:
        scenes: Lista de objetos scene com 'scene_number' e 'prompt'
        style: Estilo visual
        max_parallel: Quantas gerar em paralelo (cuidado com rate limits!)
    
    Returns:
        Lista de scenes com campo 'image_url' adicionado
    """
    results = []
    
    # Por enquanto, sequencial (pra não estourar rate limit)
    # Depois pode usar ThreadPoolExecutor pra paralelizar
    for scene in scenes:
        result = generate_scene_image(
            prompt=scene["prompt"],
            scene_number=scene["scene_number"],
            style=style
        )
        
        # Adicionar URL da imagem ao objeto scene
        scene["image_url"] = result["image_url"]
        scene["image_generated"] = result["success"]
        
        results.append(scene)
    
    return results


def _generate_placeholder_image(scene_number: int, prompt: str) -> dict:
    """
    Gera imagem placeholder quando Stability AI não disponível
    Usa PIL para criar uma imagem colorida simples
    """
    try:
        from PIL import Image, ImageDraw, ImageFont
        
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
            "note": "Placeholder image (Stability AI not configured)"
        }
        
    except ImportError:
        # Se PIL não tiver instalado, retorna só URL mock
        return {
            "success": False,
            "image_path": None,
            "image_url": f"/api/files/mock_scene_{scene_number}.jpg",
            "note": "Mock URL (PIL not installed)"
        }


# ─── Custos Estimados ────────────────────────────────────────
"""
Stability AI SD3.5 Large Pricing (Janeiro 2025):
- Text-to-Image: $0.065 por imagem (1024x1024)
- Aspect ratio 16:9: mesmo preço

Exemplo de custos:
- 30 scenes = 30 images = $1.95
- 60 scenes = 60 images = $3.90
- 100 scenes = 100 images = $6.50

Rate Limits:
- 150 requests/minuto no plano básico
- Recomendado: gerar em batch de 10-20 por vez
"""
