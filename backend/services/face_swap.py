"""
🎭 Face Swap Service - Replicate API v1.0+ (QUALIDADE PROFISSIONAL)
────────────────────────────────────────────────────────────────
Troca rostos nas cenas geradas para colocar a pessoa nas imagens
Usa easel/advanced-face-swap - QUALIDADE COMERCIAL MÁXIMA

⭐⭐⭐⭐⭐ QUALIDADE PROFISSIONAL
✅ Preserva: skin tone, racial features, gender
✅ Mantém: lighting, clothing, aesthetics
✅ Resultado: Natural e realista
⏰ Timeout: 120 segundos (4x mais que antes)
🔄 Retry: 2 tentativas automáticas
"""

import os
import requests
import time
from typing import Optional


def face_swap_replicate(
    target_image_path: str,
    source_face_path: str,
    output_path: str = None,
    max_retries: int = 2
) -> Optional[str]:
    """
    Faz face swap usando Replicate API v1.0+ com easel/advanced-face-swap
    
    ⭐ QUALIDADE MÁXIMA: Modelo comercial de alta fidelidade
    ⏰ TIMEOUT AUMENTADO: 120 segundos (vs 30s antes)
    🔄 RETRY AUTOMÁTICO: Até 2 tentativas
    📊 LOGS DETALHADOS: Mostra progresso e tempo
    
    WORKFLOW:
    1. Gera imagem com Stability AI (cena cinematográfica)
    2. Aplica face swap (troca rosto mantendo qualidade)
    3. Resultado: Pessoa com SEU ROSTO na cena profissional
    
    Args:
        target_image_path: Caminho da imagem gerada (scene)
        source_face_path: Caminho da foto da pessoa (reference image)
        output_path: Onde salvar resultado (opcional)
        max_retries: Número máximo de tentativas (padrão: 2)
    
    Returns:
        str: Caminho da imagem com face swap, ou None se falhar
    """
    
    # Verificar se Replicate API key está configurada
    replicate_api_key = os.getenv("REPLICATE_API_KEY", "")
    
    if not replicate_api_key:
        print("⚠️ REPLICATE_API_KEY not set, skipping face swap")
        return target_image_path  # Retorna imagem original
    
    try:
        # ✅ Importar replicate 1.0+
        import replicate
        
        # ✅ CRÍTICO: Criar client com token explícito
        client = replicate.Client(api_token=replicate_api_key)
        
        print(f"🎭 Face swap: {os.path.basename(source_face_path)} → {os.path.basename(target_image_path)}")
        print(f"   Model: easel/advanced-face-swap (commercial quality)")
        
        # ─── RETRY LOGIC ──────────────────────────────────────
        for attempt in range(max_retries):
            try:
                if attempt > 0:
                    print(f"   🔄 Retry attempt {attempt + 1}/{max_retries}")
                    time.sleep(3)  # Aguarda 3s antes de retry
                
                # ─── Abrir imagens como file handles ──────────
                with open(target_image_path, "rb") as target_file:
                    with open(source_face_path, "rb") as source_file:
                        
                        # ─── Chamar Replicate API v1.0+ ──────
                        # ⭐ QUALIDADE MÁXIMA: easel/advanced-face-swap
                        # - Comercial, alta fidelidade
                        # - Preserva skin tone, features, gender
                        # - Mantém lighting e aesthetics
                        
                        print(f"   ⏳ Processing... (may take 30-60s)")
                        start_time = time.time()
                        
                        output = client.run(
                            "easel/advanced-face-swap",
                            input={
                                "target_image": target_file,  # Cena gerada
                                "swap_image": source_file,    # Rosto da pessoa
                            }
                        )
                        
                        elapsed = time.time() - start_time
                        print(f"   ⏱️ Processing time: {elapsed:.1f}s")
                
                # ─── Output é uma URL da imagem gerada ───────
                if not output:
                    print(f"   ❌ No output from face swap model")
                    if attempt < max_retries - 1:
                        continue  # Retry
                    return target_image_path
                
                # Baixar imagem gerada com TIMEOUT AUMENTADO
                print(f"   📥 Downloading result...")
                response = requests.get(output, timeout=120)  # ⏰ 120s timeout!
                
                if response.status_code != 200:
                    print(f"   ❌ Download failed: HTTP {response.status_code}")
                    if attempt < max_retries - 1:
                        continue  # Retry
                    return target_image_path
                
                # ─── Salvar imagem com face swap ─────────────
                if not output_path:
                    # Salvar no mesmo lugar com sufixo _faceswap
                    output_path = target_image_path.replace('.jpg', '_faceswap.jpg')
                
                with open(output_path, 'wb') as f:
                    f.write(response.content)
                
                # Verificar tamanho da imagem
                file_size = os.path.getsize(output_path)
                print(f"   💾 File size: {file_size / 1024:.1f} KB")
                
                print(f"✅ Face swap completed: {os.path.basename(output_path)}")
                print(f"   ⭐ Quality: Commercial grade")
                
                return output_path
                
            except requests.exceptions.Timeout:
                print(f"   ⏰ Timeout on attempt {attempt + 1} (waited 120s)")
                if attempt < max_retries - 1:
                    print(f"   🔄 Retrying in 3 seconds...")
                    continue  # Retry
                print(f"   ⚠️ All retries exhausted, using original image")
                return target_image_path
                
            except Exception as e:
                print(f"   ❌ Error on attempt {attempt + 1}: {e}")
                if attempt < max_retries - 1:
                    print(f"   🔄 Retrying in 3 seconds...")
                    continue  # Retry
                print(f"   ⚠️ All retries exhausted, using original image")
                return target_image_path
        
        # Se chegou aqui, todas as tentativas falharam
        return target_image_path
        
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
    
    ⭐ QUALIDADE: Comercial, alta fidelidade
    ⏱️ TEMPO: ~30-60s por cena
    
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
    print(f"   Model: easel/advanced-face-swap")
    print(f"   Quality: ⭐⭐⭐⭐⭐ Commercial grade")
    print(f"   Estimated time: {len(scene_images) * 45}s (~{len(scene_images) * 45 / 60:.1f} min)")
    
    swapped_images = []
    successful_swaps = 0
    failed_swaps = 0
    total_time = 0
    
    for i, scene_path in enumerate(scene_images, 1):
        print(f"\n📸 Processing scene {i}/{len(scene_images)}...")
        
        start = time.time()
        swapped_path = face_swap_replicate(
            target_image_path=scene_path,
            source_face_path=reference_face_path
        )
        elapsed = time.time() - start
        total_time += elapsed
        
        swapped_images.append(swapped_path)
        
        if swapped_path != scene_path:
            successful_swaps += 1
        else:
            failed_swaps += 1
        
        # Mostrar progresso
        remaining = len(scene_images) - i
        eta = (total_time / i) * remaining if i > 0 else 0
        print(f"   Progress: {i}/{len(scene_images)} | ETA: {eta:.0f}s")
    
    avg_time = total_time / len(scene_images) if scene_images else 0
    
    print(f"\n{'='*60}")
    print(f"✅ Face swap completed!")
    print(f"   Success: {successful_swaps}/{len(scene_images)} scenes")
    if failed_swaps > 0:
        print(f"   Failed: {failed_swaps} scenes (using original)")
    print(f"   ⏱️ Average time per scene: {avg_time:.1f}s")
    print(f"   ⏱️ Total face swap time: {total_time:.1f}s (~{total_time/60:.1f} min)")
    print(f"   ⭐ Quality: Commercial grade")
    print(f"{'='*60}\n")
    
    return swapped_images
