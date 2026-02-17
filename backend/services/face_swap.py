"""
🎭 Face Swap Service - Replicate API v1.0+
────────────────────────────────────────────────────────────────
Troca rostos nas cenas geradas para colocar a pessoa nas imagens
Usa Replicate API v1.0+ para face swap de alta qualidade

✅ CORRIGIDO: Compatível com replicate>=1.0.0
"""

import os
import requests
from typing import Optional


def face_swap_replicate(
    target_image_path: str,
    source_face_path: str,
    output_path: str = None
) -> Optional[str]:
    """
    Faz face swap usando Replicate API v1.0+
    
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
        # ✅ NOVO: Importar replicate 1.0+
        import replicate
        
        # ✅ CRÍTICO: Criar client com token explícito
        client = replicate.Client(api_token=replicate_api_key)
        
        print(f"🎭 Face swap: {os.path.basename(source_face_path)} → {os.path.basename(target_image_path)}")
        
        # ─── Abrir imagens como file handles ──────────────────
        with open(target_image_path, "rb") as target_file:
            with open(source_face_path, "rb") as source_file:
                
                # ─── Chamar Replicate API v1.0+ ──────────────
                # Modelo: yan-ops/face_swap
                output = client.run(
                    "yan-ops/face_swap:d5900f9ebed33e7ae6a43c6cb24e3d21f886c239bcb72b082312c8e0db367c",
                    input={
                        "target_image": target_file,
                        "swap_image": source_file,
                    }
                )
        
        # ─── Output é uma URL da imagem gerada ───────────────
        if not output:
            print(f"❌ Face swap failed: no output")
            return target_image_path
        
        # Baixar imagem gerada
        response = requests.get(output, timeout=30)
        
        if response.status_code != 200:
            print(f"❌ Face swap failed: HTTP {response.status_code}")
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
