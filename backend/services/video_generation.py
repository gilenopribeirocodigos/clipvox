"""
🎬 ClipVox - Video Generation Service (Nano Banana Pro via PiAPI)
────────────────────────────────────────────────────────────────────
Sem referência  → Nano Banana Pro text-to-image
Com referência  → Nano Banana Pro + image_urls (face consistency)
                  Mantém o rosto da pessoa em TODAS as cenas

Auth: X-API-Key (PiAPI)
Endpoint: api.piapi.ai/api/v1/task
Model: gemini | task_type: nano-banana-pro

🆕 FEATURES:
- ✅ Aspect Ratio (16:9, 9:16, 1:1, 4:3)
- ✅ Visual Styles (10+ estilos)
- ✅ Reference Image → face consistency via image_urls
- ✅ $0.105/imagem (Nano Banana Pro)
"""

import os
import base64
import time
import requests
from typing import Optional
from PIL import Image

from config import (
    UPLOAD_DIR,
    VISUAL_STYLES,
    R2_BUCKET_NAME,
    R2_PUBLIC_URL,
    get_r2_client
)

# ── PiAPI ────────────────────────────────────────────────────────────────────
PIAPI_KEY      = os.getenv("PIAPI_API_KEY", "")
PIAPI_BASE_URL = "https://api.piapi.ai/api/v1/task"

# ── imgbb (para hospedar imagem de referência) ────────────────────────────────
IMGBB_KEY = os.getenv("IMGBB_API_KEY", "")

# ── Aspect ratio ──────────────────────────────────────────────────────────────
NB_ASPECT_RATIO = {
    "16:9": "16:9",
    "9:16": "9:16",
    "1:1":  "1:1",
    "4:3":  "4:3",
}


# ══════════════════════════════════════════════════════════════════════════════
# CLOUDFLARE R2 UPLOAD
# ══════════════════════════════════════════════════════════════════════════════
def upload_to_r2(local_path: str, r2_key: str) -> Optional[str]:
    try:
        r2_client = get_r2_client()
        if not r2_client:
            return None
        with open(local_path, 'rb') as f:
            r2_client.put_object(
                Bucket=R2_BUCKET_NAME,
                Key=r2_key,
                Body=f,
                ContentType='image/jpeg'
            )
        public_url = f"{R2_PUBLIC_URL}/{r2_key}"
        print(f"✅ Uploaded to R2: {public_url}")
        return public_url
    except Exception as e:
        print(f"❌ R2 upload error: {e}")
        return None


# ══════════════════════════════════════════════════════════════════════════════
# IMGBB UPLOAD (para hospedar imagem de referência como URL pública)
# ══════════════════════════════════════════════════════════════════════════════
def _upload_reference_to_imgbb(image_path: str) -> Optional[str]:
    """Faz upload da imagem de referência para imgbb → URL pública para PiAPI."""
    if not IMGBB_KEY:
        print("   ⚠️ IMGBB_API_KEY não configurada — sem referência de rosto")
        return None
    try:
        with open(image_path, "rb") as f:
            b64 = base64.b64encode(f.read()).decode("utf-8")
        resp = requests.post(
            f"https://api.imgbb.com/1/upload?key={IMGBB_KEY}",
            data={"image": b64, "name": f"clipvox_ref_{int(time.time())}"},
            timeout=60
        )
        if resp.status_code == 200:
            url = resp.json().get("data", {}).get("url")
            if url:
                time.sleep(2)  # CDN propagation
                print(f"   ✅ imgbb ref: {url}")
                return url
        print(f"   ❌ imgbb falhou: HTTP {resp.status_code}")
        return None
    except Exception as e:
        print(f"   ❌ imgbb erro: {e}")
        return None


# ══════════════════════════════════════════════════════════════════════════════
# NANO BANANA PRO — IMAGE GENERATION VIA PIAPI
# ══════════════════════════════════════════════════════════════════════════════
def _generate_nano_banana_image(
    prompt: str,
    scene_number: int,
    style: str = "realistic",
    aspect_ratio: str = "16:9",
    reference_image_url: Optional[str] = None,
) -> Optional[str]:
    """
    Chama Nano Banana Pro via PiAPI.

    COM referência → image_urls = [reference_image_url] (mantém rosto)
    SEM referência → text-to-image puro

    Retorna URL da imagem gerada, ou None se falhar.
    """
    if not PIAPI_KEY:
        print("   ❌ PIAPI_API_KEY não configurada")
        return None

    # Enriquece o prompt com o estilo
    style_config = VISUAL_STYLES.get(style, VISUAL_STYLES["realistic"])
    style_prefix = style_config.get("prefix", "")
    full_prompt  = f"{style_prefix}, {prompt}" if style_prefix else prompt

    nb_aspect = NB_ASPECT_RATIO.get(aspect_ratio, "16:9")

    # ── Payload ────────────────────────────────────────────────────────────────
    payload_input = {
        "prompt":       full_prompt[:2000],
        "aspect_ratio": nb_aspect,
    }

    if reference_image_url:
        print(f"   🎭 Mode: Nano Banana Pro + face reference")
        payload_input["image_urls"] = [reference_image_url]
    else:
        print(f"   🎨 Mode: Nano Banana Pro text-to-image")

    payload = {
        "model":     "gemini",
        "task_type": "nano-banana-pro",
        "input":     payload_input,
    }

    headers = {
        "Content-Type": "application/json",
        "X-API-Key":    PIAPI_KEY,
    }

    print(f"   📐 {nb_aspect} | {style}")

    try:
        resp = requests.post(PIAPI_BASE_URL, headers=headers, json=payload, timeout=30)
        print(f"   📥 HTTP {resp.status_code}: {resp.text[:300]}")

        data = resp.json()

        # PiAPI retorna task_id para polling
        task_id = (
            data.get("data", {}).get("task_id")
            or data.get("task_id")
        )
        if not task_id:
            print(f"   ❌ task_id não encontrado: {data}")
            return None

        print(f"   ✅ Task criada: {task_id}")

        # ── Polling ────────────────────────────────────────────────────────────
        poll_headers = {"X-API-Key": PIAPI_KEY}
        for elapsed in range(10, 301, 10):
            time.sleep(10)
            try:
                r  = requests.get(
                    f"{PIAPI_BASE_URL}/{task_id}",
                    headers=poll_headers,
                    timeout=15
                )
                td = r.json()

                status = (
                    td.get("data", {}).get("status")
                    or td.get("status", "")
                )
                print(f"   ⏳ Cena {scene_number} — {status} ({elapsed}s)")

                if status in ("completed", "succeed", "success"):
                    output = (
                        td.get("data", {}).get("output", {})
                        or td.get("output", {})
                    )
                    img_url = (
                        (output.get("image_urls") or [None])[0]   # ← Nano Banana retorna lista
                        or output.get("image_url")
                        or output.get("url")
                        or (output.get("images") or [{}])[0].get("url")
                        or (td.get("data", {}).get("images") or [{}])[0].get("url")
                    )
                    if img_url:
                        print(f"   ✅ Imagem pronta: {img_url[:80]}")
                        return img_url
                    print(f"   ❌ Nenhuma imagem no resultado: {td}")
                    return None

                elif status in ("failed", "error"):
                    error_msg = (
                        td.get("data", {}).get("error", {}).get("message", "")
                        or str(td.get("error", ""))
                    )
                    print(f"   ❌ Task falhou: {error_msg}")
                    return None

            except Exception as e:
                print(f"   ⚠️ Polling erro: {e}")

        print(f"   ❌ Timeout (300s) — Cena {scene_number}")
        return None

    except Exception as e:
        print(f"   ❌ Exceção: {e}")
        import traceback; traceback.print_exc()
        return None


# ══════════════════════════════════════════════════════════════════════════════
# DOWNLOAD IMAGEM + UPLOAD R2
# ══════════════════════════════════════════════════════════════════════════════
def _download_and_upload(
    img_url: str,
    scene_number: int,
    job_id: str,
    aspect_ratio: str,
    resolution: str,
    mode: str
) -> dict:
    try:
        r = requests.get(img_url, timeout=60)
        if r.status_code != 200:
            return _generate_placeholder_image(scene_number, "")

        filename   = f"scene_{scene_number:03d}.jpg"
        local_path = os.path.join(UPLOAD_DIR, filename)
        with open(local_path, "wb") as f:
            f.write(r.content)

        r2_key = f"jobs/{job_id}/{filename}" if job_id else f"scenes/{filename}"
        r2_url = upload_to_r2(local_path, r2_key)

        print(f"✅ Scene {scene_number} done")
        return {
            "success":      True,
            "scene_number": scene_number,
            "image_path":   local_path,
            "image_url":    r2_url or img_url,
            "r2_url":       r2_url,
            "prompt_used":  "",
            "mode":         mode,
            "aspect_ratio": aspect_ratio,
            "resolution":   resolution,
        }
    except Exception as e:
        print(f"❌ Download/upload error scene {scene_number}: {e}")
        return _generate_placeholder_image(scene_number, "")


# ══════════════════════════════════════════════════════════════════════════════
# PLACEHOLDER
# ══════════════════════════════════════════════════════════════════════════════
def _generate_placeholder_image(scene_number: int, prompt: str) -> dict:
    img        = Image.new('RGB', (1280, 720), color=(40, 40, 50))
    filename   = f"scene_{scene_number:03d}_placeholder.jpg"
    local_path = os.path.join(UPLOAD_DIR, filename)
    img.save(local_path)
    return {
        "success":      False,
        "scene_number": scene_number,
        "image_path":   local_path,
        "image_url":    f"/api/files/{filename}",
        "r2_url":       None,
        "prompt_used":  prompt[:100],
        "mode":         "placeholder",
        "aspect_ratio": "16:9",
        "resolution":   "720p",
    }


# ══════════════════════════════════════════════════════════════════════════════
# GENERATE SCENE IMAGE
# ══════════════════════════════════════════════════════════════════════════════
def generate_scene_image(
    prompt: str,
    scene_number: int,
    style: str = "realistic",
    aspect_ratio: str = "16:9",
    resolution: str = "720p",
    reference_image_path: str = None,
    reference_imgbb_url: str = None,
    job_id: str = ""
) -> dict:
    """
    Gera uma imagem via Nano Banana Pro (PiAPI).
    COM referência → inclui image_urls para manter rosto
    SEM referência → text-to-image puro
    """
    print(f"\n🎨 Generating scene {scene_number} [{aspect_ratio}, {resolution}, {style}]")

    # ── Obter URL pública da referência ────────────────────────────────────────
    ref_url = None
    if reference_imgbb_url:
        ref_url = reference_imgbb_url
    elif reference_image_path and os.path.exists(reference_image_path):
        ref_url = _upload_reference_to_imgbb(reference_image_path)

    nb_url = _generate_nano_banana_image(
        prompt=prompt,
        scene_number=scene_number,
        style=style,
        aspect_ratio=aspect_ratio,
        reference_image_url=ref_url,
    )

    if not nb_url:
        print(f"   ⚠️ Nano Banana falhou — usando placeholder")
        return _generate_placeholder_image(scene_number, prompt)

    mode = "nano-banana-face-ref" if ref_url else "nano-banana-text2image"
    return _download_and_upload(nb_url, scene_number, job_id, aspect_ratio, resolution, mode)


# ══════════════════════════════════════════════════════════════════════════════
# GENERATE SCENES BATCH
# ══════════════════════════════════════════════════════════════════════════════
def generate_scenes_batch(
    scenes: list,
    style: str = "realistic",
    aspect_ratio: str = "16:9",
    resolution: str = "720p",
    reference_image_path: str = None,
    job_id: str = ""
) -> list:
    """
    Gera imagens para múltiplas cenas via Nano Banana Pro (PiAPI).
    Sobe a referência (foto do rosto) para imgbb UMA VEZ e reutiliza em todas.
    """
    results          = []
    successful_count = 0

    print(f"\n🎨 Generating {len(scenes)} scene images via Nano Banana Pro (PiAPI)...")
    print(f"   Style:        {style}")
    print(f"   Aspect Ratio: {aspect_ratio}")
    print(f"   Resolution:   {resolution}")

    # ── Hospedar referência UMA vez para todas as cenas ────────────────────────
    cached_ref_url = None
    if reference_image_path and os.path.exists(reference_image_path):
        print(f"   🎭 Reference:  {os.path.basename(reference_image_path)}")
        print(f"   Mode:         Nano Banana Pro — face reference")
        print(f"   📤 Uploading reference to imgbb...")
        cached_ref_url = _upload_reference_to_imgbb(reference_image_path)
        if cached_ref_url:
            print(f"   🔗 Ref URL cached para todas as cenas")
        else:
            print(f"   ⚠️ Sem referência — usando text-to-image")
    else:
        print(f"   Mode:         Nano Banana Pro — text-to-image")

    for scene in scenes:
        result = generate_scene_image(
            prompt=scene["prompt"],
            scene_number=scene["scene_number"],
            style=style,
            aspect_ratio=aspect_ratio,
            resolution=resolution,
            reference_image_path=None,          # já processada acima
            reference_imgbb_url=cached_ref_url, # URL pública reutilizada
            job_id=job_id
        )

        if result["success"]:
            successful_count += 1
        results.append(result)

        # Delay entre cenas para evitar rate limit
        if scene != scenes[-1]:
            time.sleep(3)

    print(f"\n✅ Generated {successful_count}/{len(scenes)} scenes successfully")
    return results


# ══════════════════════════════════════════════════════════════════════════════
# Compatibilidade com código antigo
# ══════════════════════════════════════════════════════════════════════════════
def upload_to_r2_compat(local_path: str, r2_key: str) -> Optional[str]:
    return upload_to_r2(local_path, r2_key)
