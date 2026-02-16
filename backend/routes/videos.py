from fastapi import APIRouter, UploadFile, File, Form, HTTPException, BackgroundTasks
from fastapi.responses import JSONResponse
import os
import uuid
import time
from config import UPLOAD_DIR, CREDITS_PER_VIDEO
from services.audio_analysis import analyze_audio_cinematic
from services.scene_calculator import calculate_cinematic_scenes, get_scene_summary
from services.ai_concept import generate_creative_concept_with_prompts
from services.video_generation import generate_scenes_batch

router = APIRouter()

# In-memory storage for demo (em produção usar DB)
jobs_db = {}


# 🆕 TRIM VIRTUAL (SEM FFMPEG)
# ────────────────────────────────────────────────────────────────
def get_virtual_duration(duration: str) -> int:
    """
    ⚡ TRIM VIRTUAL - Não corta o áudio, apenas retorna a duração desejada
    
    Esta função NÃO usa pydub/ffmpeg (que exigem binários do sistema).
    Em vez disso, retornamos a duração que o usuário quer, e o código
    usa isso para calcular o número correto de cenas.
    
    O áudio completo é analisado pelo librosa (para BPM, energia, etc),
    mas a DURAÇÃO é sobrescrita para calcular apenas as cenas necessárias.
    
    Args:
        duration: "10", "30", "60", "120", "full", ou número em segundos
    
    Returns:
        int: Duração em segundos, ou None se "full"
    """
    if duration == "full":
        return None
    
    try:
        duration_seconds = int(duration)
        print(f"⏱️ Virtual trim: Using {duration_seconds}s for scene calculations")
        print(f"   (Audio will be analyzed completely, but scenes calculated for {duration_seconds}s only)")
        return duration_seconds
        
    except Exception as e:
        print(f"❌ Error parsing duration: {e}")
        print(f"   Using full audio duration")
        return None


@router.post("/generate")
async def generate_video(
    audio: UploadFile = File(...),
    description: str = Form(""),
    style: str = Form("realistic"),
    duration: str = Form("full"),             # 🆕 FEATURE 1
    aspect_ratio: str = Form("16:9"),         # 🆕 FEATURE 2
    resolution: str = Form("720p"),           # 🆕 FEATURE 3
    ref_image: UploadFile = File(None),       # 🆕 FEATURE 5 (opcional)
    background_tasks: BackgroundTasks = None
):
    """
    Inicia geração de videoclipe
    
    🆕 Novos parâmetros:
        - duration: "10", "30", "60", "120", "full", ou número em segundos
        - aspect_ratio: "16:9", "9:16", "1:1", "4:3"
        - resolution: "720p", "1080p"
        - ref_image: Imagem de referência (opcional)
    
    Returns:
        job_id para acompanhar progresso
    """
    
    # Validate audio file
    if not audio.content_type.startswith("audio/"):
        raise HTTPException(400, "File must be an audio file")
    
    # Generate job ID
    job_id = str(uuid.uuid4())
    
    # Save audio file
    audio_filename = f"{job_id}_{audio.filename}"
    audio_path = os.path.join(UPLOAD_DIR, audio_filename)
    
    with open(audio_path, "wb") as f:
        content = await audio.read()
        f.write(content)
    
    # 🆕 FEATURE 5: Save reference image if provided
    ref_image_path = None
    if ref_image:
        print(f"🖼️ Reference image uploaded: {ref_image.filename}")
        ref_image_filename = f"{job_id}_ref_{ref_image.filename}"
        ref_image_path = os.path.join(UPLOAD_DIR, ref_image_filename)
        
        with open(ref_image_path, "wb") as f:
            ref_content = await ref_image.read()
            f.write(ref_content)
        
        print(f"✅ Reference image saved: {os.path.basename(ref_image_path)}")
    
    # Initialize job
    jobs_db[job_id] = {
        "id": job_id,
        "status": "pending",
        "progress": 0,
        "current_step": "plan",
        "audio_filename": audio.filename,
        "audio_path": audio_path,
        "description": description,
        "style": style,
        "duration": duration,              # 🆕
        "aspect_ratio": aspect_ratio,      # 🆕
        "resolution": resolution,          # 🆕
        "ref_image_path": ref_image_path,  # 🆕
        "created_at": time.time()
    }
    
    # Start processing in background
    background_tasks.add_task(process_video_pipeline, job_id)
    
    return {
        "job_id": job_id,
        "status": "processing",
        "message": "Video generation started",
        "config": {
            "duration": duration,
            "aspect_ratio": aspect_ratio,
            "resolution": resolution,
            "style": style,
            "has_reference_image": ref_image is not None
        }
    }


@router.get("/status/{job_id}")
async def get_job_status(job_id: str):
    """
    Retorna status atual do job
    Frontend chama isso em polling
    """
    if job_id not in jobs_db:
        raise HTTPException(404, "Job not found")
    
    job = jobs_db[job_id]
    
    return {
        "id": job["id"],
        "status": job["status"],
        "progress": job["progress"],
        "current_step": job.get("current_step"),
        "audio_duration": job.get("audio_duration"),
        "audio_bpm": job.get("audio_bpm"),
        "audio_key": job.get("audio_key"),
        "creative_concept": job.get("creative_concept"),
        "scenes": job.get("scenes"),
        "segments": job.get("segments"),
        "output_file": job.get("output_file"),
        "error_message": job.get("error_message"),
        # 🆕 Config usado
        "config": {
            "duration": job.get("duration"),
            "aspect_ratio": job.get("aspect_ratio"),
            "resolution": job.get("resolution"),
            "style": job.get("style"),
            "has_reference_image": job.get("ref_image_path") is not None
        }
    }


def process_video_pipeline(job_id: str):
    """
    Pipeline completo de geração cinematográfica
    🆕 Com suporte a duration, aspect_ratio, resolution, ref_image
    
    ⚡ TRIM VIRTUAL:
    - Não corta o áudio fisicamente (sem pydub/ffmpeg)
    - Analisa áudio completo (BPM, energia, etc)
    - Sobrescreve duration para calcular cenas corretas
    - Resultado: 15-20 cenas para 30s (não 41!)
    """
    job = jobs_db[job_id]
    
    try:
        # ─── STEP 1: PLAN ─────────────────────────────────────
        update_job(job_id, status="processing", progress=5, current_step="plan")
        time.sleep(1)
        
        # ⚡ TRIM VIRTUAL: Pega duração desejada (não corta áudio)
        # ────────────────────────────────────────────────────────
        virtual_duration = get_virtual_duration(job["duration"])
        
        # ─── STEP 2: INPUT ANALYZING ──────────────────────────
        update_job(job_id, progress=10, current_step="analyzing")
        
        print(f"🎵 Analyzing audio: {job['audio_path']}")
        print(f"   Duration preset: {job['duration']}")
        if virtual_duration:
            print(f"   Virtual duration override: {virtual_duration}s")
        print(f"   Aspect ratio: {job['aspect_ratio']}")
        print(f"   Resolution: {job['resolution']}")
        
        # ⚡ Passa virtual_duration para o analyzer
        audio_metadata = analyze_audio_cinematic(
            job["audio_path"],
            duration_override=virtual_duration
        )
        
        job["audio_duration"] = audio_metadata["duration"]
        job["audio_bpm"] = audio_metadata["bpm"]
        job["audio_key"] = audio_metadata["key"]
        job["audio_energy_profile"] = audio_metadata["energy_profile"]
        
        update_job(job_id, progress=18)
        time.sleep(1)
        
        # ─── STEP 3: CALCULATE SCENES ─────────────────────────
        update_job(job_id, progress=22, current_step="calculating_scenes")
        
        print(f"🎬 Calculating cinematic scenes...")
        print(f"   Based on duration: {audio_metadata['duration']}s")
        
        scene_structure = calculate_cinematic_scenes(
            audio_metadata,
            job["description"]
        )
        
        print(get_scene_summary(scene_structure))
        
        job["total_scenes"] = scene_structure["total_scenes"]
        job["total_segments"] = scene_structure["total_segments"]
        
        update_job(job_id, progress=28)
        
        # ─── STEP 4: CREATIVE CONCEPT ─────────────────────────
        update_job(job_id, progress=30, current_step="creative")
        
        print(f"🎨 Generating creative concept with Claude API...")
        creative_concept = generate_creative_concept_with_prompts(
            audio_metadata,
            scene_structure,
            job["description"],
            job["style"]
        )
        
        job["creative_concept"] = creative_concept
        
        update_job(job_id, progress=58)
        time.sleep(2)
        
        # ─── STEP 5: GENERATE SCENE IMAGES ────────────────────
        update_job(job_id, progress=60, current_step="scenes")
        
        print(f"🎨 Generating {len(creative_concept['scenes'])} scene images with Stability AI...")
        print(f"   Style: {job['style']}")
        print(f"   Aspect ratio: {job['aspect_ratio']}")
        print(f"   Resolution: {job['resolution']}")
        if job.get('ref_image_path'):
            print(f"   Reference image: {os.path.basename(job['ref_image_path'])}")
        print(f"📤 Uploading to CloudFlare R2...")
        
        scenes_with_images = generate_scenes_batch(
            creative_concept["scenes"],
            style=job["style"],
            aspect_ratio=job["aspect_ratio"],
            resolution=job["resolution"],
            reference_image_path=job.get("ref_image_path"),
            job_id=job_id
        )
        
        job["scenes"] = scenes_with_images
        
        # Calcular progresso
        scenes_generated = sum(1 for s in scenes_with_images if s.get("success", False))
        progress_scenes = 60 + int((scenes_generated / len(scenes_with_images)) * 20)
        update_job(job_id, progress=min(progress_scenes, 80))
        
        print(f"✅ Generated {scenes_generated}/{len(scenes_with_images)} scenes successfully")
        print(f"☁️ Images stored in CloudFlare R2")
        
        time.sleep(1)
        
        # ─── STEP 6: VIDEO SEGMENTS ───────────────────────────
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
        
        # ─── STEP 7: MERGE FINAL ──────────────────────────────
        update_job(job_id, progress=98, current_step="final")
        
        print(f"✅ Video generation completed: {job_id}")
        print(f"   Generated {job['total_scenes']} scenes in {job['total_segments']} segments.")
        print(f"   Images generated successfully: {scenes_generated}/{len(scenes_with_images)}")
        print(f"   ☁️ All images are stored permanently in CloudFlare R2")
        print(f"   Configuration: {job['aspect_ratio']}, {job['resolution']}, {job['style']}")
        
        update_job(
            job_id,
            status="completed",
            progress=100,
            current_step="done",
            output_file=f"video_{job_id}.mp4"
        )
        
    except Exception as e:
        print(f"❌ Error processing job {job_id}: {e}")
        import traceback
        traceback.print_exc()
        
        update_job(
            job_id,
            status="failed",
            error_message=str(e)
        )


def update_job(job_id: str, **kwargs):
    """Helper pra atualizar job no db"""
    if job_id in jobs_db:
        jobs_db[job_id].update(kwargs)
