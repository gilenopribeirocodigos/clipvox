"""
🎬 ClipVox - Video Generation Service
──────────────────────────────────────────────────────────────
Sem referência  → Stability AI SD3.5 (text-to-image)
Com referência  → Kling IMAGE 2.1 via PiAPI (Single Reference + Character Features)
                  Mantém o rosto da pessoa em TODAS as cenas

🆕 FEATURES:
- ✅ Aspect Ratio (16:9, 9:16, 1:1, 4:3)
- ✅ Resolution (720p, 1080p)
- ✅ Visual Styles (10+ estilos)
- ✅ Reference Image → Kling IMAGE 2.1 (face consistente!)
"""

import os
import base64
import time
import requests
from typing import Optional
from PIL import Image
import io

from config import (
    STABILITY_API_KEY,
    UPLOAD_DIR,
    VISUAL_STYLES,
    R2_BUCKET_NAME,
    R2_PUBLIC_URL,
    get_r2_client
)

# ── PiAPI config (mesmo usado no kling_video.py) ──────────────────
PIAPI_KEY   = os.getenv("PIAPI_API_KEY") or os.getenv("PIAPI_KEY")
IMGBB_KEY   = os.getenv("IMGBB_API_KEY", "")
PIAPI_BASE  = "https://api.piapi.ai/api/v1/task"

# ── Aspect ratio → string aceita pelo Kling ───────────────────────
KLING_ASPECT_RATIO = {
    "16:9": "16:9",
    "9:16": "9:16",
    "1:1":  "1:1",
    "4:3":  "4:3",
}

ASPECT_RATIO_DIMENSIONS = {
    "16:9": {"720p": (1280, 720),  "1080p": (1920, 1080)},
    "9:16": {"720p": (720, 1280),  "1080p": (1080, 1920)},
    "1:1":  {"720p": (1024, 1024), "1080p": (1536, 1536)},
    "4:3":  {"720p": (1024, 768),  "1080p": (1536, 1152)},
}


# ═══════════════════════════════════════════════════════════════
# IMGBB REHOST (igual ao kling_video.py)
# ═══════════════════════════════════════════════════════════════
def _rehost_imgbb(image_path: str, name: str = "ref") -> Optional[str]:
    """Faz upload de arquivo local para imgbb e retorna URL pública."""
    if not IMGBB_KEY:
        print("   ❌ IMGBB_API_KEY não configurada")
        return None
    try:
        with open(image_path, "rb") as f:
            b64 = base64.b64encode(f.read()).decode("utf-8")
        resp = requests.post(
            f"https://api.imgbb.com/1/upload?key={IMGBB_KEY}",
            data={"image": b64, "name": name},
            timeout=60
        )
        if resp.status_code == 200:
            url = resp.json().get("data", {}).get("url")
            if url:
                time.sleep(2)  # CDN propagation
                print(f"   ✅ imgbb URL: {url}")
                return url
        print(f"   ❌ imgbb falhou (HTTP {resp.status_code})")
        return None
    except Exception as e:
        print(f"   ❌ imgbb erro: {e}")
        return None


# ═══════════════════════════════════════════════════════════════
# KLING IMAGE 2.1 — Single Reference (Character Features)
# ═══════════════════════════════════════════════════════════════
def _generate_kling_image(
    prompt: str,
    reference_url: str,
    aspect_ratio: str = "16:9",
    style: str = "realistic",
    scene_number: int = 1
) -> Optional[str]:
    """
    Chama Kling IMAGE 2.1 via PiAPI com Single Reference (Character Features).
    Retorna URL da imagem gerada, ou None se falhar.
    """
    if not PIAPI_KEY:
        print("   ❌ PIAPI_KEY não configurada")
        return None

    # Enriquece o prompt com o estilo
    style_config = VISUAL_STYLES.get(style, VISUAL_STYLES["realistic"])
    style_prefix = style_config.get("prefix", "")
    full_prompt   = f"{style_prefix}, {prompt}" if style_prefix else prompt

    headers = {
        "x-api-key":    PIAPI_KEY,
        "Content-Type": "application/json"
    }

    payload = {
        "model":     "kling",
        "task_type": "image_generation",
        "input": {
            "prompt":               full_prompt[:500],
            "aspect_ratio":         KLING_ASPECT_RATIO.get(aspect_ratio, "16:9"),
            "image_reference":      "subject",        # Single Reference - Character Features
            "image_reference_url":  reference_url,
            "negative_prompt":      "blurry, distorted face, different person, wrong identity",
        }
    }

    print(f"   🎨 Kling IMAGE 2.1 — Cena {scene_number} (Single Reference)")
    print(f"   📐 Aspect ratio: {aspect_ratio}")

    try:
        resp = requests.post(PIAPI_BASE, headers=headers, json=payload, timeout=30)
        print(f"   📥 HTTP {resp.status_code}: {resp.text[:300]}")

        if resp.status_code not in (200, 201):
            print(f"   ❌ PiAPI erro: {resp.text[:200]}")
            return None

        data      = resp.json()
        task_data = data.get("data", data)

        if task_data.get("status") in ("failed", "error"):
            print(f"   ❌ Task falhou: {task_data.get('error')}")
            return None

        task_id = task_data.get("task_id") or data.get("task_id")
        if not task_id:
            print(f"   ❌ task_id não encontrado: {data}")
            return None

        print(f"   ✅ Task criada: {task_id}")

        # ── Polling ───────────────────────────────────────────
        for elapsed in range(5, 301, 5):
            time.sleep(5)
            try:
                r         = requests.get(f"{PIAPI_BASE}/{task_id}", headers=headers, timeout=15)
                td        = r.json().get("data", r.json())
                status    = td.get("status", "")
                print(f"   ⏳ Cena {scene_number} — {status} ({elapsed}s)")

                if status in ("completed", "succeed", "success"):
                    # Extrair URL da imagem
                    output = td.get("output", {})
                    works  = output.get("works", [])
                    if works:
                        img_url = (works[0].get("image", {}).get("resource_without_watermark")
                                   or works[0].get("image", {}).get("resource")
                                   or works[0].get("url"))
                        if img_url:
                            print(f"   ✅ Imagem pronta: {img_url[:80]}")
                            return img_url
                    # Fallback
                    img_url = output.get("image_url") or output.get("url") or td.get("image_url")
                    if img_url:
                        print(f"   ✅ Imagem pronta: {img_url[:80]}")
                        return img_url
                    print(f"   ❌ URL não encontrada na resposta: {td}")
                    return None

                elif status in ("failed", "error", "cancelled"):
                    print(f"   ❌ Falhou: {td.get('error')}")
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
        print(f"❌ Error uploading to R2: {e}")
        return None


# ═══════════════════════════════════════════════════════════════
# RESIZE (para Stability AI image-to-image — mantido como fallback)
# ═══════════════════════════════════════════════════════════════
def resize_image_to_aspect_ratio(image_path, aspect_ratio="16:9", resolution="720p"):
    try:
        target_w, target_h = ASPECT_RATIO_DIMENSIONS[aspect_ratio][resolution]
        img = Image.open(image_path)
        ow, oh  = img.size
        ta = target_w / target_h
        oa = ow / oh
        if oa > ta:
            nw = int(oh * ta)
            l  = (ow - nw) // 2
            img = img.crop((l, 0, l + nw, oh))
        else:
            nh = int(ow / ta)
            t  = (oh - nh) // 2
            img = img.crop((0, t, ow, t + nh))
        img  = img.resize((target_w, target_h), Image.Resampling.LANCZOS)
        ext  = os.path.splitext(image_path)[1]
        out  = image_path.replace(ext, f"_resized_{aspect_ratio.replace(':','x')}_{resolution}{ext}")
        img.save(out, quality=95, optimize=True)
        return out
    except Exception as e:
        print(f"⚠️ Resize error: {e}")
        return image_path


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
    reference_imgbb_url: str = None,   # ← URL já rehostada (para não repetir upload)
    job_id: str = ""
) -> dict:
    """
    Gera uma imagem para uma cena.

    COM referência  → Kling IMAGE 2.1 (Single Reference, Character Features)
    SEM referência  → Stability AI SD3.5 (text-to-image)
    """

    # ── COM REFERÊNCIA: Kling IMAGE 2.1 ──────────────────────────
    if reference_image_path and os.path.exists(reference_image_path):
        print(f"\n🎨 Generating scene {scene_number} [{aspect_ratio}, {resolution}, {style}]")
        print(f"   Mode: Kling IMAGE 2.1 (Single Reference — Character Features)")

        ref_url = reference_imgbb_url  # Usa URL já upada se disponível

        if not ref_url:
            print(f"   📤 Fazendo upload da referência para imgbb...")
            ref_url = _rehost_imgbb(reference_image_path, f"clipvox_ref_{job_id}")

        if not ref_url:
            print(f"   ⚠️ Falha no imgbb — usando Stability AI como fallback")
            return _generate_stability(prompt, scene_number, style, aspect_ratio,
                                       resolution, reference_image_path, job_id)

        kling_url = _generate_kling_image(
            prompt=prompt,
            reference_url=ref_url,
            aspect_ratio=aspect_ratio,
            style=style,
            scene_number=scene_number
        )

        if not kling_url:
            print(f"   ⚠️ Kling falhou — usando Stability AI como fallback")
            return _generate_stability(prompt, scene_number, style, aspect_ratio,
                                       resolution, reference_image_path, job_id)

        # Baixar imagem gerada pelo Kling e fazer upload pro R2
        return _download_and_upload(kling_url, scene_number, job_id, aspect_ratio, resolution,
                                     mode="kling-single-reference")

    # ── SEM REFERÊNCIA: Stability AI ─────────────────────────────
    return _generate_stability(prompt, scene_number, style, aspect_ratio,
                                resolution, None, job_id)


# ═══════════════════════════════════════════════════════════════
# STABILITY AI (text-to-image ou image-to-image)
# ═══════════════════════════════════════════════════════════════
def _generate_stability(
    prompt, scene_number, style, aspect_ratio, resolution,
    reference_image_path, job_id
) -> dict:
    if not STABILITY_API_KEY:
        return _generate_placeholder_image(scene_number, prompt)

    try:
        url          = "https://api.stability.ai/v2beta/stable-image/generate/sd3"
        style_config = VISUAL_STYLES.get(style, VISUAL_STYLES["realistic"])
        enriched     = f"{style_config['prefix']}, {prompt}"

        payload = {
            "prompt":        enriched,
            "output_format": "jpeg",
            "model":         "sd3.5-large",
        }

        mode  = "text-to-image"
        files = {"none": ''}

        if reference_image_path and os.path.exists(reference_image_path):
            resized = resize_image_to_aspect_ratio(reference_image_path, aspect_ratio, resolution)
            with open(resized, 'rb') as f:
                files = {"image": f.read()}
            mode = "image-to-image"
            payload["mode"]     = "image-to-image"
            payload["strength"] = 0.7
        else:
            payload["aspect_ratio"] = aspect_ratio

        headers = {
            "Authorization": f"Bearer {STABILITY_API_KEY}",
            "Accept":        "application/json"
        }

        print(f"🎨 Generating scene {scene_number} [{aspect_ratio}, {resolution}, {style}]")
        print(f"   Mode: {mode} (aspect_ratio {'in payload' if mode == 'text-to-image' else 'inherited from image'})")

        request_files = {"none": ''} if mode == "text-to-image" else {"image": files["image"]}
        response = requests.post(url, headers=headers, files=request_files, data=payload, timeout=60)

        if response.status_code != 200:
            print(f"❌ Stability AI error: {response.status_code}")
            return _generate_placeholder_image(scene_number, prompt)

        data = response.json()
        if "image" not in data:
            return _generate_placeholder_image(scene_number, prompt)

        image_data = base64.b64decode(data["image"])
        filename   = f"scene_{scene_number:03d}.jpg"
        local_path = os.path.join(UPLOAD_DIR, filename)
        with open(local_path, "wb") as f:
            f.write(image_data)

        r2_key = f"jobs/{job_id}/{filename}" if job_id else f"scenes/{filename}"
        r2_url = upload_to_r2(local_path, r2_key)

        print(f"✅ Scene {scene_number} generated and uploaded")
        return {
            "success": True, "scene_number": scene_number,
            "image_path": local_path,
            "image_url":  r2_url or f"/api/files/{filename}",
            "r2_url":     r2_url,
            "prompt_used": enriched[:100],
            "mode": mode, "aspect_ratio": aspect_ratio, "resolution": resolution
        }

    except Exception as e:
        print(f"❌ Stability error scene {scene_number}: {e}")
        return _generate_placeholder_image(scene_number, prompt)


# ═══════════════════════════════════════════════════════════════
# DOWNLOAD KLING IMAGE + UPLOAD R2
# ═══════════════════════════════════════════════════════════════
def _download_and_upload(img_url, scene_number, job_id, aspect_ratio, resolution, mode) -> dict:
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

        print(f"✅ Scene {scene_number} generated and uploaded")
        return {
            "success": True, "scene_number": scene_number,
            "image_path": local_path,
            "image_url":  r2_url or img_url,
            "r2_url":     r2_url,
            "prompt_used": "",
            "mode": mode, "aspect_ratio": aspect_ratio, "resolution": resolution
        }
    except Exception as e:
        print(f"❌ Download/upload error scene {scene_number}: {e}")
        return _generate_placeholder_image(scene_number, "")


# ═══════════════════════════════════════════════════════════════
# PLACEHOLDER
# ═══════════════════════════════════════════════════════════════
def _generate_placeholder_image(scene_number: int, prompt: str) -> dict:
    img      = Image.new('RGB', (1280, 720), color=(40, 40, 50))
    filename = f"scene_{scene_number:03d}_placeholder.jpg"
    local_path = os.path.join(UPLOAD_DIR, filename)
    img.save(local_path)
    return {
        "success": False, "scene_number": scene_number,
        "image_path": local_path,
        "image_url":  f"/api/files/{filename}",
        "r2_url":     None, "prompt_used": prompt[:100],
        "mode": "placeholder", "aspect_ratio": "16:9", "resolution": "720p"
    }


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
    Gera imagens para múltiplas cenas em batch.

    COM referência → Kling IMAGE 2.1 para TODAS as cenas
                     Faz o upload da referência UMA VEZ só para o imgbb
    SEM referência → Stability AI para todas as cenas
    """
    results = []
    successful_count = 0

    print(f"\n🎨 Generating {len(scenes)} scene images...")
    print(f"   Style: {style}")
    print(f"   Aspect Ratio: {aspect_ratio}")
    print(f"   Resolution: {resolution}")

    # ── Se tem referência: faz upload imgbb UMA VEZ ──────────────
    reference_imgbb_url = None
    if reference_image_path and os.path.exists(reference_image_path):
        print(f"   🎭 Reference Image: {os.path.basename(reference_image_path)}")
        print(f"   📤 Uploading reference to imgbb (uma vez para todas as cenas)...")
        reference_imgbb_url = _rehost_imgbb(reference_image_path, f"clipvox_ref_{job_id}")
        if reference_imgbb_url:
            print(f"   ✅ Referência pronta: {reference_imgbb_url}")
            print(f"   🎨 Modo: Kling IMAGE 2.1 (Single Reference — Character Features)")
        else:
            print(f"   ⚠️ imgbb falhou — usando Stability AI image-to-image como fallback")
    else:
        print(f"   Mode: Stability AI text-to-image")

    print("📤 Uploading to CloudFlare R2...")

    for scene in scenes:
        result = generate_scene_image(
            prompt=scene["prompt"],
            scene_number=scene["scene_number"],
            style=style,
            aspect_ratio=aspect_ratio,
            resolution=resolution,
            reference_image_path=reference_image_path,
            reference_imgbb_url=reference_imgbb_url,  # ← passa URL já upada
            job_id=job_id
        )

        if result["success"]:
            successful_count += 1
        results.append(result)

        # Delay entre cenas com Kling para evitar rate limit
        if reference_imgbb_url and scene != scenes[-1]:
            time.sleep(3)

    print(f"✅ Generated {successful_count}/{len(scenes)} scenes successfully")
    return results
