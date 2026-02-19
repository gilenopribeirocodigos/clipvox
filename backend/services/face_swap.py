"""
🎭 Face Swap Service - PiAPI Integration
────────────────────────────────────────────────────────────────
Troca rostos nas cenas geradas usando PiAPI Faceswap API

✅ QUALIDADE: ⭐⭐⭐⭐ Profissional
✅ VELOCIDADE: Rápido (~10-20s por imagem)
✅ CUSTO: $0.02 por face swap
✅ CONFIÁVEL: Usado por desenvolvedores profissionais
✅ API: RESTful, async, webhook support
"""

import os
import requests
import time
from typing import Optional


def face_swap_piapi(
    target_image_path: str,
    source_face_path: str,
    output_path: str = None,
    max_retries: int = 2,
    timeout: int = 90
) -> Optional[str]:
    """
    Faz face swap usando PiAPI Faceswap API
    
    ⭐ QUALIDADE: Profissional, excellent blending
    ⚡ VELOCIDADE: 10-20s por imagem
    💰 CUSTO: $0.02 por face swap
    🔄 RETRY: Até 2 tentativas automáticas
    
    Args:
        target_image_path: Caminho da imagem gerada (scene)
        source_face_path: Caminho da foto da pessoa (reference image)
        output_path: Onde salvar resultado (opcional)
        max_retries: Número máximo de tentativas (padrão: 2)
        timeout: Timeout em segundos (padrão: 90s)
    
    Returns:
        str: Caminho da imagem com face swap, ou None se falhar
    """
    
    # Verificar se PiAPI API key está configurada
    piapi_api_key = os.getenv("PIAPI_API_KEY", "")
    
    if not piapi_api_key:
        print("⚠️ PIAPI_API_KEY not set, skipping face swap")
        return target_image_path  # Retorna imagem original
    
    try:
        print(f"🎭 Face swap: {os.path.basename(source_face_path)} → {os.path.basename(target_image_path)}")
        print(f"   API: PiAPI Faceswap (professional quality)")
        
        # ─── RETRY LOGIC ──────────────────────────────────────
        for attempt in range(max_retries):
            try:
                if attempt > 0:
                    print(f"   🔄 Retry attempt {attempt + 1}/{max_retries}")
                    time.sleep(3)  # Aguarda 3s antes de retry
                
                # ─── Ler imagens como base64 ou usar URLs ──────
                # PiAPI aceita URLs ou base64
                # Vamos usar file upload direto
                
                start_time = time.time()
                
                # ─── STEP 1: Criar task (async) ──────
                url = "https://api.piapi.ai/api/v1/task"
                
                headers = {
                    "x-api-key": piapi_api_key,
                    "Content-Type": "application/json"
                }
                
                # Ler imagens e converter para base64
                import base64
                
                with open(target_image_path, "rb") as f:
                    target_b64 = base64.b64encode(f.read()).decode('utf-8')
                
                with open(source_face_path, "rb") as f:
                    source_b64 = base64.b64encode(f.read()).decode('utf-8')
                
                payload = {
                    "model": "Qubico/image-toolkit",
                    "task_type": "face-swap",
                    "input": {
                        "target_image": f"data:image/jpeg;base64,{target_b64}",
                        "swap_image": f"data:image/jpeg;base64,{source_b64}"
                    }
                }
                
                print(f"   📤 Submitting task to PiAPI...")
                
                response = requests.post(url, json=payload, headers=headers, timeout=30)
                
                if response.status_code != 200:
                    print(f"   ❌ API error: HTTP {response.status_code}")
                    print(f"   Response: {response.text}")
                    if attempt < max_retries - 1:
                        continue  # Retry
                    return target_image_path
                
                result = response.json()
                
                if result.get("code") != 200:
                    print(f"   ❌ API error: {result.get('message')}")
                    if attempt < max_retries - 1:
                        continue  # Retry
                    return target_image_path
                
                task_id = result.get("data", {}).get("task_id")
                
                if not task_id:
                    print(f"   ❌ No task_id returned")
                    if attempt < max_retries - 1:
                        continue  # Retry
                    return target_image_path
                
                print(f"   ✅ Task created: {task_id}")
                
                # ─── STEP 2: Poll for result ──────
                fetch_url = f"https://api.piapi.ai/api/v1/task/{task_id}/fetch"
                
                print(f"   ⏳ Waiting for result...")
                
                max_polls = 30  # 30 tentativas = ~90s
                poll_interval = 3  # 3s entre tentativas
                
                for poll in range(max_polls):
                    time.sleep(poll_interval)
                    
                    fetch_response = requests.get(fetch_url, headers=headers, timeout=30)
                    
                    if fetch_response.status_code != 200:
                        print(f"   ⚠️ Fetch error: HTTP {fetch_response.status_code}")
                        continue
                    
                    fetch_result = fetch_response.json()
                    
                    if fetch_result.get("code") != 200:
                        print(f"   ⚠️ Fetch error: {fetch_result.get('message')}")
                        continue
                    
                    task_data = fetch_result.get("data", {})
                    status = task_data.get("status")
                    
                    if status == "processing" or status == "pending":
                        # Ainda processando
                        if (poll + 1) % 5 == 0:  # A cada 15s
                            print(f"   ⏳ Still processing... ({poll * poll_interval}s)")
                        continue
                    
                    elif status == "succeeded":
                        # Sucesso!
                        output_data = task_data.get("output")
                        
                        if not output_data:
                            print(f"   ❌ No output in result")
                            break
                        
                        # Output pode ser lista ou string
                        if isinstance(output_data, list) and len(output_data) > 0:
                            image_url = output_data[0]
                        elif isinstance(output_data, str):
                            image_url = output_data
                        else:
                            print(f"   ❌ Invalid output format")
                            break
                        
                        elapsed = time.time() - start_time
                        print(f"   ⏱️ Processing time: {elapsed:.1f}s")
                        
                        # ─── STEP 3: Download resultado ──────
                        print(f"   📥 Downloading result...")
                        
                        img_response = requests.get(image_url, timeout=60)
                        
                        if img_response.status_code != 200:
                            print(f"   ❌ Download failed: HTTP {img_response.status_code}")
                            break
                        
                        # ─── Salvar imagem com face swap ─────
                        if not output_path:
                            output_path = target_image_path.replace('.jpg', '_faceswap.jpg')
                        
                        with open(output_path, 'wb') as f:
                            f.write(img_response.content)
                        
                        file_size = os.path.getsize(output_path)
                        print(f"   💾 File size: {file_size / 1024:.1f} KB")
                        print(f"✅ Face swap completed: {os.path.basename(output_path)}")
                        print(f"   ⭐ Quality: Professional (PiAPI)")
                        
                        return output_path
                    
                    elif status == "failed":
                        error = task_data.get("error", {})
                        print(f"   ❌ Task failed: {error.get('message', 'Unknown error')}")
                        break
                    
                    else:
                        print(f"   ⚠️ Unknown status: {status}")
                        continue
                
                # Se chegou aqui, timeout ou falha
                print(f"   ⏰ Timeout waiting for result")
                if attempt < max_retries - 1:
                    continue  # Retry
                
                return target_image_path
                
            except requests.exceptions.Timeout:
                print(f"   ⏰ Request timeout on attempt {attempt + 1}")
                if attempt < max_retries - 1:
                    continue  # Retry
                print(f"   ⚠️ All retries exhausted, using original image")
                return target_image_path
                
            except Exception as e:
                print(f"   ❌ Error on attempt {attempt + 1}: {str(e)}")
                if attempt < max_retries - 1:
                    continue  # Retry
                print(f"   ⚠️ All retries exhausted, using original image")
                return target_image_path
        
        # Se chegou aqui, todas as tentativas falharam
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
    Aplica face swap em múltiplas cenas usando PiAPI
    
    ⭐ QUALIDADE: Professional
    💰 CUSTO: $0.02 por imagem
    
    Args:
        scene_images: Lista de caminhos das imagens das cenas
        reference_face_path: Caminho da foto da pessoa
    
    Returns:
        list: Lista de caminhos das imagens com face swap
    """
    
    if not reference_face_path or not os.path.exists(reference_face_path):
        print("⚠️ No reference face image, skipping face swap")
        return scene_images
    
    print(f"\n{'='*60}")
    print(f"🎭 Applying face swap to {len(scene_images)} scenes...")
    print(f"   Reference face: {os.path.basename(reference_face_path)}")
    print(f"   API: PiAPI Faceswap")
    print(f"   Quality: ⭐⭐⭐⭐ Professional")
    print(f"   Estimated cost: ${len(scene_images) * 0.02:.2f}")
    print(f"   Estimated time: {len(scene_images) * 15}s (~{len(scene_images) * 15 / 60:.1f} min)")
    print(f"{'='*60}\n")
    
    swapped_images = []
    successful_swaps = 0
    failed_swaps = 0
    total_time = 0
    
    for i, scene_path in enumerate(scene_images, 1):
        print(f"📸 Processing scene {i}/{len(scene_images)}...")
        
        start = time.time()
        swapped_path = face_swap_piapi(
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
        avg_time = total_time / i
        eta = avg_time * remaining
        print(f"   Progress: {i}/{len(scene_images)} | Avg: {avg_time:.1f}s/scene | ETA: {eta:.0f}s\n")
    
    avg_time = total_time / len(scene_images) if scene_images else 0
    
    print(f"\n{'='*60}")
    print(f"✅ Face swap batch completed!")
    print(f"   Success: {successful_swaps}/{len(scene_images)} scenes")
    if failed_swaps > 0:
        print(f"   Failed: {failed_swaps} scenes (using original)")
    print(f"   ⏱️ Average time per scene: {avg_time:.1f}s")
    print(f"   ⏱️ Total face swap time: {total_time:.1f}s (~{total_time/60:.1f} min)")
    print(f"   💰 Estimated cost: ${successful_swaps * 0.02:.2f}")
    print(f"   ⭐ Quality: Professional (PiAPI)")
    print(f"{'='*60}\n")
    
    return swapped_images
