from fastapi import APIRouter, UploadFile, File, Form, HTTPException, BackgroundTasks
from fastapi.responses import JSONResponse
from typing import Optional
import os
import uuid
import time
from config import UPLOAD_DIR, CREDITS_PER_VIDEO
from services.audio_analysis import analyze_audio_cinematic
from services.scene_calculator import calculate_cinematic_scenes, get_scene_summary
from services.ai_concept import generate_creative_concept_with_prompts
from services.video_generation import generate_scenes_batch
from services.kling_video import generate_videos_batch   # ✅ NOVO

router = APIRouter()

# In-memory storage for demo (em produção usar DB)
jobs_db = {}


# ─── TRIM VIRTUAL (SEM FFMPEG) ────────────────────────────────
def get_virtual_duration(duration: str) -> int:
    if duration == "full":
        return None
    try:
        duration_seconds = int(duration)
        print(f"⏱️ Virtual trim: Using {duration_seconds}s for scene calculations")
        return duration_seconds
    except Exception as e:
        print(f"❌ Error parsing duration: {e}")
        return None


# ═══════════════════════════════════════════════════════════════
# POST /generate — inicia pipeline completo
# ═══════════════════════════════════════════════════════════════
@router.post("/generate")
async def generate_video(
    audio:        UploadFile      = File(...),
    description:  str             = Form(""),
    style:        str             = Form("realistic"),
    duration:     str             = Form("full"),
    aspect_ratio: str             = Form("16:9"),
    resolution:   str             = Form("720p"),
    ref_image:    Optional[UploadFile] = File(None),    # ✅ CORREÇÃO 4
    background_tasks: BackgroundTasks = None
):
    # Validate audio file — aceita content-types variados
    ALLOWED_AUDIO = ["audio/", "application/octet-stream", "video/mp4", "application/mp3", "application/mpeg"]
    if not any(audio.content_type.startswith(t) for t in ALLOWED_AUDIO):
        # fallback: aceitar pela extensão se content-type falhar
        audio_ext = (audio.filename or "").lower().split(".")[-1]
        if audio_ext not in ["mp3", "wav", "ogg", "m4a", "flac", "aac", "mp4"]:
            raise HTTPException(400, f"Formato não suportado: {audio.content_type}")

    job_id = str(uuid.uuid4())

    # Salvar áudio
    audio_filename = f"{job_id}_{audio.filename}"
    audio_path     = os.path.join(UPLOAD_DIR, audio_filename)
    with open(audio_path, "wb") as f:
        f.write(await audio.read())

    # Salvar imagem de referência (opcional)
    ref_image_path = None
    if ref_image:
        ref_image_filename = f"{job_id}_ref_{ref_image.filename}"
        ref_image_path     = os.path.join(UPLOAD_DIR, ref_image_filename)
        with open(ref_image_path, "wb") as f:
            f.write(await ref_image.read())
        print(f"✅ Imagem de referência salva: {os.path.basename(ref_image_path)}")

    # Inicializar job
    jobs_db[job_id] = {
        "id":             job_id,
        "status":         "pending",
        "progress":       0,
        "current_step":   "plan",
        "audio_filename": audio.filename,
        "audio_path":     audio_path,
        "description":    description,
        "style":          style,
        "duration":       duration,
        "aspect_ratio":   aspect_ratio,
        "resolution":     resolution,
        "ref_image_path": ref_image_path,
        "created_at":     time.time(),
        # ✅ NOVO: campos para vídeos Kling
        "video_clips":    None,
        "videos_status":  "pending"   # pending | processing | completed | failed
    }

    background_tasks.add_task(process_video_pipeline, job_id)

    return {
        "job_id":  job_id,
        "status":  "processing",
        "message": "Video generation started",
        "config": {
            "duration":             duration,
            "aspect_ratio":         aspect_ratio,
            "resolution":           resolution,
            "style":                style,
            "has_reference_image":  ref_image is not None
        }
    }


# ═══════════════════════════════════════════════════════════════
# GET /status/{job_id} — retorna status atual
# ═══════════════════════════════════════════════════════════════
@router.get("/status/{job_id}")
async def get_job_status(job_id: str):
    if job_id not in jobs_db:
        raise HTTPException(404, "Job not found")

    job = jobs_db[job_id]

    return {
        "id":               job["id"],
        "status":           job["status"],
        "progress":         job["progress"],
        "current_step":     job.get("current_step"),
        "audio_duration":   job.get("audio_duration"),
        "audio_bpm":        job.get("audio_bpm"),
        "audio_key":        job.get("audio_key"),
        "creative_concept": job.get("creative_concept"),
        "scenes":           job.get("scenes"),
        "segments":         job.get("segments"),
        "output_file":      job.get("output_file"),
        "error_message":    job.get("error_message"),
        # ✅ NOVO: vídeos Kling
        "video_clips":      job.get("video_clips"),
        "videos_status":    job.get("videos_status"),
        "config": {
            "duration":            job.get("duration"),
            "aspect_ratio":        job.get("aspect_ratio"),
            "resolution":          job.get("resolution"),
            "style":               job.get("style"),
            "has_reference_image": job.get("ref_image_path") is not None
        }
    }


# ═══════════════════════════════════════════════════════════════
# ✅ NOVO — POST /generate-clips/{job_id}
# Dispara geração de vídeos Kling para as cenas já geradas
# ═══════════════════════════════════════════════════════════════
@router.post("/generate-clips/{job_id}")
async def generate_video_clips(
    job_id:           str,
    background_tasks: BackgroundTasks,
    mode:             str = "std"   # "std" ou "pro"
):
    """
    Converte as imagens de cenas já geradas em clipes de vídeo
    usando Kling AI via PiAPI.

    Chame este endpoint APÓS o job estar com status "completed"
    e ter scenes com image_url.

    Args:
        job_id: ID do job já processado
        mode:   "std" (~$0.14/clipe) ou "pro" (~$0.28/clipe)
    """
    if job_id not in jobs_db:
        raise HTTPException(404, "Job not found")

    job = jobs_db[job_id]

    if job["status"] != "completed":
        raise HTTPException(400, f"Job ainda não concluído (status: {job['status']}). Aguarde as imagens serem geradas primeiro.")

    scenes = job.get("scenes")
    if not scenes:
        raise HTTPException(400, "Nenhuma cena encontrada neste job")

    # Verificar se já está gerando
    if job.get("videos_status") == "processing":
        return {"message": "Geração de vídeos já em andamento", "job_id": job_id}

    # Marcar como processando
    jobs_db[job_id]["videos_status"] = "processing"
    jobs_db[job_id]["video_clips"]   = None

    # Disparar geração em background
    background_tasks.add_task(
        process_video_clips,
        job_id = job_id,
        mode   = mode
    )

    bpm = job.get("audio_bpm", 120)
    total_scenes = len([s for s in scenes if s.get("success", False)])

    return {
        "job_id":        job_id,
        "status":        "processing",
        "message":       f"Gerando {total_scenes} clipes de vídeo com Kling AI...",
        "estimated_cost": f"~${total_scenes * (0.14 if mode == 'std' else 0.28):.2f}",
        "mode":          mode
    }


# ═══════════════════════════════════════════════════════════════
# BACKGROUND TASK — pipeline de imagens (já existia)
# ═══════════════════════════════════════════════════════════════
def process_video_pipeline(job_id: str):
    job = jobs_db[job_id]

    try:
        # STEP 1: PLAN
        update_job(job_id, status="processing", progress=5, current_step="plan")
        time.sleep(1)

        virtual_duration = get_virtual_duration(job["duration"])

        # STEP 2: ANALYZING
        update_job(job_id, progress=10, current_step="analyzing")
        print(f"🎵 Analisando áudio: {job['audio_path']}")

        audio_metadata = analyze_audio_cinematic(
            job["audio_path"],
            duration_override=virtual_duration
        )

        job["audio_duration"]      = audio_metadata["duration"]
        job["audio_bpm"]           = audio_metadata["bpm"]
        job["audio_key"]           = audio_metadata["key"]
        job["audio_energy_profile"] = audio_metadata["energy_profile"]

        update_job(job_id, progress=18)
        time.sleep(1)

        # STEP 3: CALCULATE SCENES
        update_job(job_id, progress=22, current_step="calculating_scenes")
        print(f"🎬 Calculando cenas cinematográficas...")

        scene_structure = calculate_cinematic_scenes(audio_metadata, job["description"])
        print(get_scene_summary(scene_structure))

        job["total_scenes"]    = scene_structure["total_scenes"]
        job["total_segments"]  = scene_structure["total_segments"]

        update_job(job_id, progress=28)

        # STEP 4: CREATIVE CONCEPT
        update_job(job_id, progress=30, current_step="creative")
        print(f"🎨 Gerando conceito criativo com Claude API...")

        creative_concept = generate_creative_concept_with_prompts(
            audio_metadata,
            scene_structure,
            job["description"],
            job["style"]
        )
        job["creative_concept"] = creative_concept

        update_job(job_id, progress=58)
        time.sleep(2)

        # STEP 5: GENERATE SCENE IMAGES (Stability AI)
        update_job(job_id, progress=60, current_step="scenes")
        print(f"🎨 Gerando {len(creative_concept['scenes'])} imagens com Stability AI...")

        scenes_with_images = generate_scenes_batch(
            creative_concept["scenes"],
            style                  = job["style"],
            aspect_ratio           = job["aspect_ratio"],
            resolution             = job["resolution"],
            reference_image_path   = job.get("ref_image_path"),
            job_id                 = job_id
        )

        job["scenes"] = scenes_with_images

        scenes_generated = sum(1 for s in scenes_with_images if s.get("success", False))
        update_job(job_id, progress=min(60 + int((scenes_generated / len(scenes_with_images)) * 20), 80))

        print(f"✅ {scenes_generated}/{len(scenes_with_images)} imagens geradas")

        time.sleep(1)

        # STEP 6: VIDEO SEGMENTS (estrutura)
        update_job(job_id, progress=85, current_step="segments")

        segments = scene_structure["segments"]
        for segment in segments:
            segment["scenes_with_images"] = [
                s for s in scenes_with_images
                if s.get("scene_number") in segment.get("scenes", [])
            ]
        job["segments"] = segments

        update_job(job_id, progress=95)
        time.sleep(1)

        # STEP 7: FINAL
        update_job(job_id, progress=98, current_step="final")
        print(f"✅ Pipeline concluído: {job_id}")

        update_job(
            job_id,
            status        = "completed",
            progress      = 100,
            current_step  = "done",
            output_file   = f"video_{job_id}.mp4",
            videos_status = "ready"   # ✅ Pronto para gerar vídeos Kling
        )

    except Exception as e:
        print(f"❌ Erro no job {job_id}: {e}")
        import traceback
        traceback.print_exc()
        update_job(job_id, status="failed", error_message=str(e))


# ═══════════════════════════════════════════════════════════════
# ✅ NOVO — BACKGROUND TASK: gerar clipes Kling
# ═══════════════════════════════════════════════════════════════
def process_video_clips(job_id: str, mode: str = "std"):
    """
    Converte imagens de cenas em clipes de vídeo usando Kling (PiAPI).
    Executado em background após o pipeline principal.
    """
    job = jobs_db.get(job_id)
    if not job:
        return

    try:
        scenes      = job.get("scenes", [])
        bpm         = job.get("audio_bpm", 120)
        aspect_ratio = job.get("aspect_ratio", "16:9")

        # Filtrar apenas cenas com imagem gerada com sucesso
        valid_scenes = [s for s in scenes if s.get("success", False) and s.get("image_url")]

        print(f"\n🎬 Gerando {len(valid_scenes)} clipes de vídeo (Kling/{mode})")
        print(f"   Job: {job_id} | BPM: {bpm:.0f} | AR: {aspect_ratio}")

        video_results = generate_videos_batch(
            scenes       = valid_scenes,
            bpm          = bpm,
            aspect_ratio = aspect_ratio,
            mode         = mode
        )

        success_count = sum(1 for r in video_results if r.get("success", False))
        print(f"✅ Clipes gerados: {success_count}/{len(valid_scenes)}")

        jobs_db[job_id]["video_clips"]  = video_results
        jobs_db[job_id]["videos_status"] = "completed"

    except Exception as e:
        print(f"❌ Erro ao gerar clipes para job {job_id}: {e}")
        import traceback
        traceback.print_exc()
        jobs_db[job_id]["videos_status"] = "failed"
        jobs_db[job_id]["videos_error"]  = str(e)


# ─── HELPER ───────────────────────────────────────────────────
def update_job(job_id: str, **kwargs):
    if job_id in jobs_db:
        jobs_db[job_id].update(kwargs)
