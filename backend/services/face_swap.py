"""
🎭 Face Swap Service - Replicate API
────────────────────────────────────────────────────────────────
Troca rostos nas cenas geradas para colocar a pessoa nas imagens
Usa Replicate API para face swap de alta qualidade

Similar ao FREEBEAT: pessoa aparece nas cenas!
"""

import os
import requests
import base64
from typing import Optional
from PIL import Image
import io


def face_swap_replicate(
    target_image_path: str,
    source_face_path: str,
    output_path: str = None
) -> Optional[str]:
    """
    Faz face swap usando Replicate API
    
    Args:
        target_image_path: Caminho da imagem gerada (scene)
        source_face_path: Caminho da foto da pessoa (reference image)
        output_path: Onde salvar resultado (opcional)
    
    Returns:
        str: Caminho da imagem com face swap, ou None se falhar
    """
    
    # Verificar se Replicate API key está configurada
    replicate_api_key = os.getenv("REPLICATE_API_KEY", "")
    
    if not replicate_api_key:
        print("⚠️ REPLICATE_API_KEY not set, skipping face swap")
        return target_image_path  # Retorna imagem original
    
    try:
        import replicate
        
        print(f"🎭 Face swap: {os.path.basename(source_face_path)} → {os.path.basename(target_image_path)}")
        
        # ─── Converter imagens para base64 ───────────────────
        with open(target_image_path, "rb") as f:
            target_b64 = base64.b64encode(f.read()).decode()
        
        with open(source_face_path, "rb") as f:
            source_b64 = base64.b64encode(f.read()).decode()
        
        # ─── Chamar Replicate API ────────────────────────────
        # Usando modelo yan-ops/face_swap (rápido e qualidade boa)
        output = replicate.run(
            "yan-ops/face_swap:d5900f9ebed33e7ae6a43c6cb24cont3d21f886c239bcb72b082312c8e",
            input={
                "target_image": f"data:image/jpeg;base64,{target_b64}",
                "swap_image": f"data:image/jpeg;base64,{source_b64}",
                "cache_days": 0  # Não cache (privacidade)
            }
        )
        
        # ─── Output é uma URL da imagem gerada ───────────────
        if not output:
            print(f"❌ Face swap failed: no output")
            return target_image_path
        
        # Baixar imagem gerada
        response = requests.get(output, timeout=30)
        
        if response.status_code != 200:
            print(f"❌ Face swap failed: {response.status_code}")
            return target_image_path
        
        # ─── Salvar imagem com face swap ─────────────────────
        if not output_path:
            # Salvar no mesmo lugar com sufixo _faceswap
            output_path = target_image_path.replace('.jpg', '_faceswap.jpg')
        
        with open(output_path, 'wb') as f:
            f.write(response.content)
        
        print(f"✅ Face swap completed: {os.path.basename(output_path)}")
        
        return output_path
        
    except ImportError:
        print("⚠️ replicate package not installed, skipping face swap")
        return target_image_path
        
    except Exception as e:
        print(f"❌ Face swap error: {e}")
        print(f"   Using original image without face swap")
        return target_image_path


def face_swap_batch(
    scene_images: list,
    reference_face_path: str
) -> list:
    """
    Aplica face swap em múltiplas cenas
    
    Args:
        scene_images: Lista de caminhos das imagens das cenas
        reference_face_path: Caminho da foto da pessoa
    
    Returns:
        list: Lista de caminhos das imagens com face swap
    """
    
    if not reference_face_path or not os.path.exists(reference_face_path):
        print("⚠️ No reference face image, skipping face swap")
        return scene_images
    
    print(f"🎭 Applying face swap to {len(scene_images)} scenes...")
    print(f"   Reference face: {os.path.basename(reference_face_path)}")
    
    swapped_images = []
    successful_swaps = 0
    
    for scene_path in scene_images:
        swapped_path = face_swap_replicate(
            target_image_path=scene_path,
            source_face_path=reference_face_path
        )
        
        swapped_images.append(swapped_path)
        
        if swapped_path != scene_path:
            successful_swaps += 1
    
    print(f"✅ Face swap completed: {successful_swaps}/{len(scene_images)} scenes")
    
    return swapped_images


# ═══════════════════════════════════════════════════════════════════
# MODELO ALTERNATIVO (caso o yan-ops não funcione)
# ═══════════════════════════════════════════════════════════════════

def face_swap_replicate_alt(
    target_image_path: str,
    source_face_path: str,
    output_path: str = None
) -> Optional[str]:
    """
    Face swap usando modelo alternativo: lucataco/faceswap
    
    Este modelo é mais estável e amplamente usado
    """
    
    replicate_api_key = os.getenv("REPLICATE_API_KEY", "")
    
    if not replicate_api_key:
        return target_image_path
    
    try:
        import replicate
        
        print(f"🎭 Face swap (alt model): {os.path.basename(source_face_path)} → {os.path.basename(target_image_path)}")
        
        # Usar URLs ou base64
        with open(target_image_path, "rb") as f:
            target_data = f.read()
        
        with open(source_face_path, "rb") as f:
            source_data = f.read()
        
        # Modelo alternativo
        output = replicate.run(
            "lucataco/faceswap:9a4863e735f490701e0ebcae4aed3857f6c0f088f79cc100bfe36c7a562cdaa4",
            input={
                "target_image": target_data,
                "swap_image": source_data
            }
        )
        
        if not output:
            return target_image_path
        
        # Download
        response = requests.get(output, timeout=30)
        
        if response.status_code != 200:
            return target_image_path
        
        if not output_path:
            output_path = target_image_path.replace('.jpg', '_faceswap.jpg')
        
        with open(output_path, 'wb') as f:
            f.write(response.content)
        
        print(f"✅ Face swap (alt) completed: {os.path.basename(output_path)}")
        
        return output_path
        
    except Exception as e:
        print(f"❌ Face swap (alt) error: {e}")
        return target_image_path
