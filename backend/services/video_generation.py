"""
🎬 ClipVox - Video Generation Service (Kling API Oficial)
──────────────────────────────────────────────────────────
Sem referência  → Kling IMAGE 2.1 text-to-image
Com referência  → Kling IMAGE 2.1 + image_reference="face" (Single Reference)
                  Mantém o rosto da pessoa em TODAS as cenas

Auth: JWT com Access Key + Secret Key (sem PiAPI!)
Endpoint: api.klingai.com/v1/images/generations

🆕 FEATURES:
- ✅ Aspect Ratio (16:9, 9:16, 1:1, 4:3)
- ✅ Resolution (1k, 2k)
- ✅ Visual Styles (10+ estilos)
- ✅ Reference Image → face consistency (Single Reference)
"""

import os
import base64
import time
import requests
import jwt
from typing import Optional
from PIL import Image

from config import (
    UPLOAD_DIR,
    VISUAL_STYLES,
    R2_BUCKET_NAME,
    R2_PUBLIC_URL,
    get_r2_client
)

# ── Kling API Oficial ─────────────────────────────────────────────
KLING_ACCESS_KEY = os.getenv("KLING_ACCESS_KEY", "")
KLING_SECRET_KEY = os.getenv("KLING_SECRET_KEY", "")
KLING_API_BASE   = "https://api.klingai.com"

# ── Aspect ratio aceito pelo Kling ────────────────────────────────
KLING_ASPECT_RATIO = {
    "16:9": "16:9",
    "9:16": "9:16",
    "1:1":  "1:1",
    "4:3":  "4:3",
}

# ── Resolution → parâmetro Kling ─────────────────────────────────
KLING_RESOLUTION = {
    "720p":  "1k",
    "1080p": "2k",
}


# ═══════════════════════════════════════════════════════════════
# JWT AUTHENTICATION
# ═══════════════════════════════════════════════════════════════
def _get_jwt_token() -> str:
    """Gera JWT token para autenticação na API oficial do Kling."""
    if not KLING_ACCESS_KEY or not KLING_SECRET_KEY:
        raise ValueError("KLING_ACCESS_KEY e KLING_SECRET_KEY são obrigatórios")

    headers = {"alg": "HS256", "typ": "JWT"}
    payload = {
        "iss": KLING_ACCESS_KEY,
        "exp": int(time.time()) + 1800,   # expira em 30min
        "nbf": int(time.time()) - 5        # válido desde 5s atrás
    }
    return jwt.encode(payload, KLING_SECRET_KEY, algorithm="HS256", headers=headers)


def _auth_headers() -> dict:
    """Retorna headers com JWT token."""
    return {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {_get_jwt_token()}"
    }


# ═══════════════════════════════════════════════════════════════
# CLOUDFLARE R2 UPLOAD
# ═══════════════════════════════════════════════════════════════
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


# ═══════════════════════════════════════════════════════════════
# IMAGE → BASE64 (para enviar referência sem depender de imgbb)
# ═══════════════════════════════════════════════════════════════
def _image_to_base64(image_path: str) -> str:
    """Converte imagem local para base64."""
    with open(image_path, "rb") as f:
        return base64.b64encode(f.read()).decode("utf-8")


# ═══════════════════════════════════════════════════════════════
# KLING IMAGE GENERATION (API OFICIAL)
# ═══════════════════════════════════════════════════════════════
def _generate_kling_image(
    prompt: str,
    scene_number: int,
    style: str = "realistic",
    aspect_ratio: str = "16:9",
    resolution: str = "720p",
    reference_image_path: str = None,
) -> Optional[str]:
    """
    Chama Kling IMAGE via API oficial.
    
    COM referência → image_reference="face" + human_fidelity
    SEM referência → text-to-image puro

    Retorna URL da imagem gerada, ou None se falhar.
    """
    if not KLING_ACCESS_KEY:
        print("   ❌ KLING_ACCESS_KEY não configurada")
        return None

    # Enriquece o prompt com o estilo
    style_config = VISUAL_STYLES.get(style, VISUAL_STYLES["realistic"])
    style_prefix = style_config.get("prefix", "")
    full_prompt   = f"{style_prefix}, {prompt}" if style_prefix else prompt

    kling_resolution = KLING_RESOLUTION.get(resolution, "1k")
    kling_aspect     = KLING_ASPECT_RATIO.get(aspect_ratio, "16:9")

    # ── Payload base ─────────────────────────────────────────
    payload = {
        "model":          "kling-v1-5",   # IMAGE 2.1
        "prompt":         full_prompt[:500],
        "negative_prompt": "blurry, distorted, deformed face, wrong person, ugly",
        "aspect_ratio":   kling_aspect,
        "image_count":    1,
    }

    # ── COM referência: face consistency ─────────────────────
    if reference_image_path and os.path.exists(reference_image_path):
        print(f"   🎭 Mode: Single Reference (face consistency)")
        ref_b64 = _image_to_base64(reference_image_path)
        payload["image"]           = ref_b64
        payload["image_reference"] = "face"     # mantém rosto
        payload["image_fidelity"]  = 0.8        # aderência à referência
        payload["human_fidelity"]  = 0.9        # fidelidade do rosto
    else:
        print(f"   🎨 Mode: text-to-image")

    print(f"   📐 {kling_aspect} | {kling_resolution} | {style}")

    try:
        resp = requests.post(
            f"{KLING_API_BASE}/v1/images/generations",
            headers=_auth_headers(),
            json=payload,
            timeout=30
        )
        print(f"   📥 HTTP {resp.status_code}: {resp.text[:300]}")

        data = resp.json()

        if data.get("code") != 0:
            print(f"   ❌ Kling API erro: {data.get('message')}")
            return None

        task_id = data.get("data", {}).get("task_id")
        if not task_id:
            print(f"   ❌ task_id não encontrado: {data}")
            return None

        print(f"   ✅ Task criada: {task_id}")

        # ── Polling ───────────────────────────────────────────
        for elapsed in range(5, 301, 5):
            time.sleep(5)
            try:
                r  = requests.get(
                    f"{KLING_API_BASE}/v1/images/generations/{task_id}",
                    headers=_auth_headers(),
                    timeout=15
                )
                td = r.json()

                if td.get("code") != 0:
                    print(f"   ❌ Polling erro: {td.get('message')}")
                    return None

                task_info = td.get("data", {})
                status    = task_info.get("task_status", "")
                print(f"   ⏳ Cena {scene_number} — {status} ({elapsed}s)")

                if status == "succeed":
                    images = task_info.get("task_result", {}).get("images", [])
                    if images:
                        img_url = images[0].get("url")
                        print(f"   ✅ Imagem pronta: {img_url[:80]}")
                        return img_url
                    print(f"   ❌ Nenhuma imagem no resultado: {task_info}")
                    return None

                elif status == "failed":
                    print(f"   ❌ Task falhou: {task_info.get('task_status_msg')}")
                    return None

            except Exception as e:
                print(f"   ⚠️ Polling erro: {e}")

        print(f"   ❌ Timeout (300s) — Cena {scene_number}")
        return None

    except Exception as e:
        print(f"   ❌ Exceção: {e}")
        import traceback; traceback.print_exc()
        return None


# ═══════════════════════════════════════════════════════════════
# DOWNLOAD IMAGEM + UPLOAD R2
# ═══════════════════════════════════════════════════════════════
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


# ═══════════════════════════════════════════════════════════════
# PLACEHOLDER
# ═══════════════════════════════════════════════════════════════
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


# ═══════════════════════════════════════════════════════════════
# GENERATE SCENE IMAGE
# ═══════════════════════════════════════════════════════════════
def generate_scene_image(
    prompt: str,
    scene_number: int,
    style: str = "realistic",
    aspect_ratio: str = "16:9",
    resolution: str = "720p",
    reference_image_path: str = None,
    reference_imgbb_url: str = None,   # ignorado — não usa mais imgbb
    job_id: str = ""
) -> dict:
    """
    Gera uma imagem via Kling API Oficial.
    COM referência → Kling IMAGE 2.1 (face reference)
    SEM referência → Kling IMAGE 2.1 (text-to-image)
    """
    print(f"\n🎨 Generating scene {scene_number} [{aspect_ratio}, {resolution}, {style}]")

    kling_url = _generate_kling_image(
        prompt=prompt,
        scene_number=scene_number,
        style=style,
        aspect_ratio=aspect_ratio,
        resolution=resolution,
        reference_image_path=reference_image_path,
    )

    if not kling_url:
        print(f"   ⚠️ Kling falhou — usando placeholder")
        return _generate_placeholder_image(scene_number, prompt)

    mode = "kling-face-reference" if reference_image_path else "kling-text2image"
    return _download_and_upload(kling_url, scene_number, job_id, aspect_ratio, resolution, mode)


# ═══════════════════════════════════════════════════════════════
# GENERATE SCENES BATCH
# ═══════════════════════════════════════════════════════════════
def generate_scenes_batch(
    scenes: list,
    style: str = "realistic",
    aspect_ratio: str = "16:9",
    resolution: str = "720p",
    reference_image_path: str = None,
    job_id: str = ""
) -> list:
    """
    Gera imagens para múltiplas cenas via Kling API Oficial.
    A referência (foto do rosto) é passada diretamente como base64 — sem imgbb!
    """
    results         = []
    successful_count = 0

    print(f"\n🎨 Generating {len(scenes)} scene images via Kling API Oficial...")
    print(f"   Style:        {style}")
    print(f"   Aspect Ratio: {aspect_ratio}")
    print(f"   Resolution:   {resolution}")

    if reference_image_path and os.path.exists(reference_image_path):
        print(f"   🎭 Reference:  {os.path.basename(reference_image_path)}")
        print(f"   Mode:         Kling IMAGE 2.1 — face reference (Single Reference)")
    else:
        print(f"   Mode:         Kling IMAGE 2.1 — text-to-image")

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

        # Delay entre cenas para evitar rate limit
        if scene != scenes[-1]:
            time.sleep(3)

    print(f"\n✅ Generated {successful_count}/{len(scenes)} scenes successfully")
    return results


# ═══════════════════════════════════════════════════════════════
# Compatibilidade com código antigo (Stability AI não é mais usado)
# ═══════════════════════════════════════════════════════════════
def upload_to_r2_compat(local_path: str, r2_key: str) -> Optional[str]:
    return upload_to_r2(local_path, r2_key)
