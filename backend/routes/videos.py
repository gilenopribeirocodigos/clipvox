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


@router.post("/generate")
async def generate_video(
    audio: UploadFile = File(...),
    description: str = Form(""),
    style: str = Form("realistic"),
    background_tasks: BackgroundTasks = None
):
    """
    Inicia geração de videoclipe
    Retorna job_id para acompanhar progresso
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
        "created_at": time.time()
    }
    
    # Start processing in background
    background_tasks.add_task(process_video_pipeline, job_id)
    
    return {
        "job_id": job_id,
        "status": "processing",
        "message": "Video generation started"
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
        "error_message": job.get("error_message")
    }


def process_video_pipeline(job_id: str):
    """
    Pipeline completo de geração cinematográfica
    Roda em background
    """
    job = jobs_db[job_id]
    
    try:
        # ─── STEP 1: PLAN ─────────────────────────────────────
        update_job(job_id, status="processing", progress=5, current_step="plan")
        time.sleep(1)
        
        # ─── STEP 2: INPUT ANALYZING ─────────────────────────
        update_job(job_id, progress=10, current_step="analyzing")
        
        print(f"🎵 Analyzing audio: {job['audio_path']}")
        audio_metadata = analyze_audio_cinematic(job["audio_path"])
        
        job["audio_duration"] = audio_metadata["duration"]
        job["audio_bpm"] = audio_metadata["bpm"]
        job["audio_key"] = audio_metadata["key"]
        job["audio_energy_profile"] = audio_metadata["energy_profile"]
        
        update_job(job_id, progress=18)
        time.sleep(1)
        
        # ─── STEP 3: CALCULATE SCENES ────────────────────────
        update_job(job_id, progress=22, current_step="calculating_scenes")
        
        print(f"🎬 Calculating cinematic scenes...")
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
        
        # ─── STEP 5: GENERATE SCENE IMAGES (STABILITY AI) ────
        update_job(job_id, progress=60, current_step="scenes")
        
        print(f"🎨 Generating {len(creative_concept['scenes'])} scene images with Stability AI...")
        
        # Gerar imagens com Stability AI
        scenes_with_images = generate_scenes_batch(
            creative_concept["scenes"],
            style=job["style"]
        )
        
        job["scenes"] = scenes_with_images
        
        # Calcular progresso dinamicamente baseado em quantas scenes foram geradas
        scenes_generated = sum(1 for s in scenes_with_images if s.get("image_generated"))
        progress_scenes = 60 + int((scenes_generated / len(scenes_with_images)) * 20)
        update_job(job_id, progress=min(progress_scenes, 80))
        
        print(f"✅ Generated {scenes_generated}/{len(scenes_with_images)} scenes successfully")
        
        time.sleep(1)
        
        # ─── STEP 6: VIDEO SEGMENTS ───────────────────────────
        update_job(job_id, progress=85, current_step="segments")
        
        # Group scenes into segments
        segments = scene_structure["segments"]
        
        # Adicionar info de quais scenes têm imagem
        for segment in segments:
            segment["scenes_with_images"] = [
                s for s in scenes_with_images 
                if s["scene_number"] in segment["scenes"]
            ]
        
        job["segments"] = segments
        
        update_job(job_id, progress=95)
        time.sleep(1)
        
        # ─── STEP 7: MERGE FINAL ──────────────────────────────
        update_job(job_id, progress=98, current_step="merge")
        
        # Mock final video (em produção, faria merge com ffmpeg)
        job["output_file"] = f"/api/files/{job_id}_final.mp4"
        
        time.sleep(1)
        
        # ─── DONE ─────────────────────────────────────────────
        update_job(
            job_id,
            status="completed",
            progress=100,
            current_step="completed"
        )
        
        print(f"✅ Video generation completed: {job_id}")
        print(f"   Generated {len(scenes_with_images)} scenes across {len(segments)} segments")
        print(f"   Successfully generated: {scenes_generated}/{len(scenes_with_images)} images")
        
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
    """Helper to update job fields"""
    if job_id in jobs_db:
        jobs_db[job_id].update(kwargs)
