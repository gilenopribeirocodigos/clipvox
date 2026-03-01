"""
🎬 ClipVox - Kling Video Generation Service (via PiAPI)
──────────────────────────────────────────────────────────────
Converte imagens de cenas em segmentos de vídeo usando Kling AI
via PiAPI (pay-as-you-go, ~$0.14 por vídeo de 5s em modo std)

Fluxo:
  1. Recebe lista de cenas com image_url (já geradas pela Stability AI)
  2. Para cada cena, envia para Kling image-to-video via PiAPI
  3. Faz polling até o vídeo ficar pronto (assíncrono)
  4. Retorna URLs dos vídeos gerados

Preços PiAPI Kling (pay-as-you-go):
  - std  5s  → ~$0.14/vídeo
  - pro  5s  → ~$0.28/vídeo
  - std  10s → ~$0.28/vídeo
"""

import os
import time
import requests
from typing import Optional

# ─── CONFIG ───────────────────────────────────────────────────
PIAPI_KEY     = os.getenv("PIAPI_API_KEY") or os.getenv("PIAPI_KEY")
PIAPI_BASE    = "https://api.piapi.ai/api/v1/task"

# Timeout e polling
MAX_WAIT_SECONDS = 300   # 5 minutos máximo por vídeo
POLL_INTERVAL    = 5     # verifica a cada 5 segundos


# ═══════════════════════════════════════════════════════════════
# CALCULAR DURAÇÃO POR CENA (baseado no BPM)
# ═══════════════════════════════════════════════════════════════
def get_clip_duration_from_bpm(bpm: float) -> int:
    """
    Retorna duração ideal do clipe baseado no BPM da música.

    Regras:
      - BPM alto (>= 140)  → 4s  (cortes rápidos, ritmo acelerado)
      - BPM médio (90-139) → 5s  (equilíbrio)
      - BPM lento (< 90)   → 6s  (câmera lenta, contemplativo)

    Kling API aceita: 5s ou 10s. Então mapeamos para 5s (mais econômico).
    Para versão futura, podemos usar 10s para BPM lento.
    """
    if bpm is None:
        return 5

    bpm = float(bpm)

    if bpm >= 140:
        return 5   # rápido → 5s (mínimo da API)
    elif bpm >= 90:
        return 5   # médio  → 5s
    else:
        return 5   # lento  → 5s (10s seria mais ideal, mas custa 2x)

    # Nota: Kling API só aceita 5 ou 10 como valores de duration.
    # Quando migrar para pro ou quiser melhor qualidade em BPM lento,
    # trocar o último return para 10.


# ═══════════════════════════════════════════════════════════════
# GERAR VÍDEO DE UMA CENA (image-to-video)
# ═══════════════════════════════════════════════════════════════
def generate_scene_video(
    image_url: str,
    prompt: str,
    scene_number: int,
    bpm: float = 120,
    aspect_ratio: str = "16:9",
    mode: str = "std"
) -> dict:
    """
    Converte uma imagem de cena em vídeo usando Kling via PiAPI.

    Args:
        image_url:    URL pública da imagem (R2 ou outro)
        prompt:       Descrição da cena para guiar o movimento
        scene_number: Número da cena (para log)
        bpm:          BPM da música (define duração)
        aspect_ratio: Proporção do vídeo (16:9, 9:16, 1:1, 4:3)
        mode:         "std" (~$0.14) ou "pro" (~$0.28) por 5s

    Returns:
        dict com: success, task_id, video_url, duration, scene_number
    """

    if not PIAPI_KEY:
        print("⚠️ PIAPI_API_KEY não configurada — pulando geração de vídeo")
        return _video_error(scene_number, "PIAPI_API_KEY not configured")

    if not image_url:
        print(f"⚠️ Cena {scene_number} sem image_url — pulando")
        return _video_error(scene_number, "No image URL provided")

    duration = get_clip_duration_from_bpm(bpm)

    # ─── Montar prompt de movimento baseado na cena ───────────
    # Kling usa o prompt para decidir COMO a cena se move
    motion_prompt = _build_motion_prompt(prompt, scene_number)

    print(f"🎬 Gerando vídeo — Cena {scene_number}")
    print(f"   Imagem: {image_url[:60]}...")
    print(f"   Duração: {duration}s | BPM: {bpm:.0f} | Modo: {mode}")
    print(f"   Aspect ratio: {aspect_ratio}")

    # ─── STEP 1: Criar task no PiAPI ──────────────────────────
    headers = {
        "x-api-key": PIAPI_KEY,
        "Content-Type": "application/json"
    }

    payload = {
        "model": "kling",
        "task_type": "video_generation",
        "input": {
            "prompt":          motion_prompt,
            "negative_prompt": "blurry, low quality, distorted, text, watermark, abrupt cuts",
            "image_url":       image_url,       # image-to-video
            "duration":        duration,
            "aspect_ratio":    aspect_ratio,
            "mode":            mode,
            "cfg_scale":       0.5              # 0=mais criativo, 1=mais fiel à imagem
        },
        "config": {
            "service_mode": ""  # "" = pay-as-you-go automático
        }
    }

    try:
        response = requests.post(
            PIAPI_BASE,
            headers=headers,
            json=payload,
            timeout=30
        )

        if response.status_code != 200:
            print(f"❌ PiAPI erro {response.status_code}: {response.text[:200]}")
            return _video_error(scene_number, f"API error {response.status_code}")

        data = response.json()

        # Verificar se task foi criada
        task_id = (
            data.get("data", {}).get("task_id") or
            data.get("task_id") or
            data.get("id")
        )

        if not task_id:
            print(f"❌ task_id não encontrado na resposta: {data}")
            return _video_error(scene_number, "No task_id in response")

        print(f"   ✅ Task criada: {task_id}")

        # ─── STEP 2: Polling até vídeo ficar pronto ───────────
        video_url = _poll_task(task_id, scene_number)

        if video_url:
            print(f"   ✅ Vídeo gerado: {video_url[:60]}...")
            return {
                "success":      True,
                "scene_number": scene_number,
                "task_id":      task_id,
                "video_url":    video_url,
                "duration":     duration,
                "mode":         mode,
                "aspect_ratio": aspect_ratio
            }
        else:
            return _video_error(scene_number, "Timeout waiting for video")

    except requests.exceptions.Timeout:
        print(f"⏱️ Timeout ao criar task para cena {scene_number}")
        return _video_error(scene_number, "Request timeout")

    except Exception as e:
        print(f"❌ Erro inesperado na cena {scene_number}: {e}")
        return _video_error(scene_number, str(e))


# ═══════════════════════════════════════════════════════════════
# POLLING — aguarda vídeo ficar pronto
# ═══════════════════════════════════════════════════════════════
def _poll_task(task_id: str, scene_number: int) -> Optional[str]:
    """
    Faz polling na PiAPI até o vídeo estar pronto.
    Retorna a URL do vídeo ou None se timeout/erro.
    """
    headers = {
        "x-api-key": PIAPI_KEY,
        "Content-Type": "application/json"
    }

    elapsed = 0
    attempt = 0

    while elapsed < MAX_WAIT_SECONDS:
        time.sleep(POLL_INTERVAL)
        elapsed += POLL_INTERVAL
        attempt += 1

        try:
            response = requests.get(
                f"{PIAPI_BASE}/{task_id}",
                headers=headers,
                timeout=15
            )

            if response.status_code != 200:
                print(f"   ⚠️ Polling erro {response.status_code} (tentativa {attempt})")
                continue

            data = response.json()

            # Extrair status (PiAPI usa estrutura aninhada)
            task_data = data.get("data", data)
            status    = task_data.get("status", "")

            print(f"   ⏳ Cena {scene_number} — status: {status} ({elapsed}s)")

            # ─── Sucesso ──────────────────────────────────────
            if status in ("completed", "succeed", "success", 99):
                video_url = _extract_video_url(task_data)
                if video_url:
                    return video_url
                else:
                    print(f"   ⚠️ Status OK mas sem video_url: {task_data}")
                    return None

            # ─── Falha ────────────────────────────────────────
            elif status in ("failed", "error", "cancelled"):
                error_msg = task_data.get("error", {}).get("message", "Unknown error")
                print(f"   ❌ Task falhou: {error_msg}")
                return None

            # ─── Ainda processando ────────────────────────────
            # status: "pending", "processing", "running" → continuar polling

        except Exception as e:
            print(f"   ⚠️ Erro no polling (tentativa {attempt}): {e}")
            continue

    print(f"   ⏱️ Timeout após {MAX_WAIT_SECONDS}s para cena {scene_number}")
    return None


# ═══════════════════════════════════════════════════════════════
# EXTRAIR URL DO VÍDEO DA RESPOSTA
# ═══════════════════════════════════════════════════════════════
def _extract_video_url(task_data: dict) -> Optional[str]:
    """
    Extrai a URL do vídeo gerado da resposta da PiAPI.
    A estrutura pode variar — tentamos múltiplos caminhos.
    """
    # Caminho 1: output.works[0].video.resource_without_watermark
    output = task_data.get("output", {})
    works  = output.get("works", [])

    if works:
        video = works[0].get("video", {})
        url = (
            video.get("resource_without_watermark") or
            video.get("resource")
        )
        if url:
            return url

    # Caminho 2: output.video_url direto
    url = output.get("video_url") or output.get("url")
    if url:
        return url

    # Caminho 3: task_data.video_url direto
    url = task_data.get("video_url") or task_data.get("url")
    if url:
        return url

    return None


# ═══════════════════════════════════════════════════════════════
# GERAR VÍDEOS EM BATCH
# ═══════════════════════════════════════════════════════════════
def generate_videos_batch(
    scenes: list,
    bpm: float = 120,
    aspect_ratio: str = "16:9",
    mode: str = "std"
) -> list:
    """
    Gera vídeos para múltiplas cenas sequencialmente.

    Args:
        scenes:       Lista de dicts com {scene_number, image_url, prompt, ...}
        bpm:          BPM da música (para calcular duração)
        aspect_ratio: Proporção do vídeo
        mode:         "std" ou "pro"

    Returns:
        Lista de dicts com resultado de cada cena
    """
    results        = []
    success_count  = 0
    total          = len(scenes)

    print(f"\n🎬 Iniciando geração de {total} vídeos com Kling AI (PiAPI)...")
    print(f"   BPM: {bpm:.0f} | Aspect Ratio: {aspect_ratio} | Modo: {mode}")
    print(f"   Duração por clipe: {get_clip_duration_from_bpm(bpm)}s")
    print(f"   Custo estimado: ~${total * (0.14 if mode == 'std' else 0.28):.2f}\n")

    for i, scene in enumerate(scenes):
        scene_number = scene.get("scene_number", i + 1)
        image_url    = scene.get("image_url") or scene.get("r2_url")
        prompt       = scene.get("prompt", "")

        print(f"[{i+1}/{total}] Processando cena {scene_number}...")

        result = generate_scene_video(
            image_url    = image_url,
            prompt       = prompt,
            scene_number = scene_number,
            bpm          = bpm,
            aspect_ratio = aspect_ratio,
            mode         = mode
        )

        if result["success"]:
            success_count += 1

        results.append(result)

    print(f"\n✅ Geração concluída: {success_count}/{total} vídeos gerados com sucesso")
    return results


# ═══════════════════════════════════════════════════════════════
# HELPERS
# ═══════════════════════════════════════════════════════════════
def _build_motion_prompt(scene_prompt: str, scene_number: int) -> str:
    """
    Constrói prompt de movimento para o Kling.
    Kling usa o prompt para determinar COMO a cena se move.
    Frases como 'slow pan', 'zoom in' guiam o movimento da câmera.
    """
    # Palavras-chave que indicam tipo de cena para escolher movimento
    scene_lower = scene_prompt.lower()

    if any(w in scene_lower for w in ["action", "fight", "run", "energy", "fast"]):
        motion = "dynamic camera movement, fast pan"
    elif any(w in scene_lower for w in ["calm", "slow", "peaceful", "serene", "night"]):
        motion = "slow gentle pan, smooth cinematic movement"
    elif any(w in scene_lower for w in ["landscape", "nature", "sky", "horizon"]):
        motion = "slow dolly forward, cinematic wide shot movement"
    elif any(w in scene_lower for w in ["close", "face", "portrait"]):
        motion = "subtle zoom in, gentle rack focus"
    else:
        motion = "smooth cinematic pan, subtle camera movement"

    # Limitar prompt a 500 caracteres (limite seguro para Kling)
    base = f"{scene_prompt[:300]}, {motion}"
    return base[:500]


def _video_error(scene_number: int, message: str) -> dict:
    """Retorna dict de erro padrão"""
    return {
        "success":      False,
        "scene_number": scene_number,
        "task_id":      None,
        "video_url":    None,
        "duration":     5,
        "error":        message
    }
