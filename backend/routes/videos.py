from fastapi import APIRouter, UploadFile, File, Form, HTTPException, BackgroundTasks
from fastapi.responses import JSONResponse, FileResponse
from typing import Optional
import os
import uuid
import time
from config import UPLOAD_DIR, CREDITS_PER_VIDEO
from services.audio_analysis import analyze_audio_cinematic
from services.scene_calculator import calculate_cinematic_scenes, get_scene_summary
from services.ai_concept import generate_creative_concept_with_prompts
from services.video_generation import generate_scenes_batch
from services.kling_video import generate_videos_batch
from services.merge_video import merge_clips_with_audio, MERGE_OUTPUT_DIR
from services.kling_lipsync import generate_lipsync

router  = APIRouter()
jobs_db = {}


def get_virtual_duration(duration: str) -> int:
    if duration == "full":
        return None
    try:
        duration_seconds = int(duration)
        print(f"Virtual trim: Using {duration_seconds}s for scene calculations")
        return duration_seconds
    except Exception as e:
        print(f"Error parsing duration: {e}")
        return None


@router.post("/generate")
async def generate_video(
    audio:        UploadFile      = File(...),
    description:  str             = Form(""),
    style:        str             = Form("realistic"),
    duration:     str             = Form("full"),
    aspect_ratio: str             = Form("16:9"),
    resolution:   str             = Form("720p"),
    ref_image:    Optional[UploadFile] = File(None),
    background_tasks: BackgroundTasks = None
):
    ALLOWED_AUDIO = ["audio/", "application/octet-stream", "video/mp4", "application/mp3", "application/mpeg"]
    if not any(audio.content_type.startswith(t) for t in ALLOWED_AUDIO):
        audio_ext = (audio.filename or "").lower().split(".")[-1]
        if audio_ext not in ["mp3", "wav", "ogg", "m4a", "flac", "aac", "mp4"]:
            raise HTTPException(400, f"Formato nao suportado: {audio.content_type}")

    job_id = str(uuid.uuid4())

    audio_filename = f"{job_id}_{audio.filename}"
    audio_path     = os.path.join(UPLOAD_DIR, audio_filename)
    with open(audio_path, "wb") as f:
        f.write(await audio.read())

    ref_image_path = None
    if ref_image:
        ref_image_filename = f"{job_id}_ref_{ref_image.filename}"
        ref_image_path     = os.path.join(UPLOAD_DIR, ref_image_filename)
        with open(ref_image_path, "wb") as f:
            f.write(await ref_image.read())

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
        "video_clips":    None,
        "videos_status":  "pending",
        "lipsync_status": None,
        "lipsync_url":    None,
        "lipsync_clips":  None,
        "vocals_path":    None,   # vocals pre-extraidos pelo StemSplit
        "merge_status":   None,
        "merge_url":      None,
    }

    background_tasks.add_task(process_video_pipeline, job_id)

    return {
        "job_id":  job_id,
        "status":  "processing",
        "message": "Video generation started",
        "config": {
            "duration":            duration,
            "aspect_ratio":        aspect_ratio,
            "resolution":          resolution,
            "style":               style,
            "has_reference_image": ref_image is not None,
        }
    }


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
        "video_clips":      job.get("video_clips"),
        "videos_status":    job.get("videos_status"),
        "lipsync_status":   job.get("lipsync_status"),
        "lipsync_url":      job.get("lipsync_url"),
        "lipsync_clips":    job.get("lipsync_clips"),
        "merge_status":     job.get("merge_status"),
        "merge_url":        job.get("merge_url"),
        "config": {
            "duration":            job.get("duration"),
            "aspect_ratio":        job.get("aspect_ratio"),
            "resolution":          job.get("resolution"),
            "style":               job.get("style"),
            "has_reference_image": job.get("ref_image_path") is not None,
        }
    }


@router.post("/generate-clips/{job_id}")
async def generate_video_clips(
    job_id:           str,
    background_tasks: BackgroundTasks,
    mode:             str = "std"
):
    if job_id not in jobs_db:
        raise HTTPException(404, "Job not found")
    job = jobs_db[job_id]
    if job["status"] != "completed":
        raise HTTPException(400, f"Job ainda nao concluido (status: {job['status']})")
    scenes = job.get("scenes")
    if not scenes:
        raise HTTPException(400, "Nenhuma cena encontrada neste job")
    if job.get("videos_status") == "processing":
        return {"message": "Geracao de videos ja em andamento", "job_id": job_id}
    jobs_db[job_id]["videos_status"] = "processing"
    jobs_db[job_id]["video_clips"]   = None
    background_tasks.add_task(process_video_clips, job_id=job_id, mode=mode)
    total_scenes = len([s for s in scenes if s.get("success", False)])
    return {
        "job_id":         job_id,
        "status":         "processing",
        "message":        f"Gerando {total_scenes} clipes de video com Kling AI...",
        "estimated_cost": f"~${total_scenes * (0.14 if mode == 'std' else 0.28):.2f}",
        "mode":           mode,
    }


@router.post("/lipsync/{job_id}")
async def generate_lipsync_video(
    job_id:           str,
    background_tasks: BackgroundTasks,
    face_image:       Optional[UploadFile] = File(None),
    face_url:         str                  = Form(""),
    model:            str                  = Form("kling"),
):
    if job_id not in jobs_db:
        raise HTTPException(404, "Job not found")
    job = jobs_db[job_id]
    audio_path = job.get("audio_path")
    if not audio_path or not os.path.exists(audio_path):
        raise HTTPException(400, "Audio do job nao encontrado")

    face_source = None
    if face_image:
        face_filename = f"{job_id}_lipsync_face_{face_image.filename}"
        face_path     = os.path.join(UPLOAD_DIR, face_filename)
        with open(face_path, "wb") as f:
            f.write(await face_image.read())
        face_source = face_path
    elif face_url:
        face_source = face_url
    elif job.get("ref_image_path") and os.path.exists(job["ref_image_path"]):
        face_source = job["ref_image_path"]
    else:
        raise HTTPException(400, "Nenhuma imagem do personagem encontrada.")

    if job.get("lipsync_status") == "processing":
        return {"message": "Lip sync ja em andamento", "job_id": job_id}

    video_clips = job.get("video_clips", [])
    successful  = [c for c in video_clips if c.get("success") and c.get("video_url")]
    total_clips = len(successful)

    jobs_db[job_id]["lipsync_status"] = "processing"
    jobs_db[job_id]["lipsync_url"]    = None
    jobs_db[job_id]["lipsync_clips"]  = None

    background_tasks.add_task(process_lipsync, job_id=job_id, face_source=face_source,
                               audio_path=audio_path, model=model)

    return {
        "job_id":      job_id,
        "status":      "processing",
        "message":     f"Lip sync iniciado em {total_clips} clipe(s) individualmente",
        "total_clips": total_clips,
        "model":       model,
    }


@router.post("/merge/{job_id}")
async def merge_final_video(job_id: str, background_tasks: BackgroundTasks):
    if job_id not in jobs_db:
        raise HTTPException(404, "Job not found")
    job = jobs_db[job_id]

    videos_ok  = job.get("videos_status") == "completed"
    lipsync_ok = job.get("lipsync_status") == "completed"

    if not videos_ok and not lipsync_ok:
        raise HTTPException(400, "Clipes ainda nao gerados. Gere os clipes primeiro.")

    clips_to_use = job.get("lipsync_clips") or job.get("video_clips", [])
    successful   = [c for c in clips_to_use if c.get("success") and c.get("video_url")]

    if not successful:
        raise HTTPException(400, "Nenhum clipe disponivel para merge")
    if job.get("merge_status") == "processing":
        return {"message": "Merge ja em andamento", "job_id": job_id}

    jobs_db[job_id]["merge_status"] = "processing"
    jobs_db[job_id]["merge_url"]    = None
    background_tasks.add_task(process_merge, job_id)

    source = "lip sync" if lipsync_ok and job.get("lipsync_clips") else "clipes originais"
    return {"job_id": job_id, "status": "processing",
            "message": f"Merge de {len(successful)} clipes ({source}) iniciado"}


@router.get("/download/{job_id}")
async def download_merged_video(job_id: str):
    if job_id not in jobs_db:
        raise HTTPException(404, "Job not found")
    job = jobs_db[job_id]
    if job.get("merge_status") != "completed":
        raise HTTPException(400, "Merge ainda nao concluido")
    local_path = os.path.join(MERGE_OUTPUT_DIR, f"final_{job_id}.mp4")
    if not os.path.exists(local_path):
        raise HTTPException(404, "Arquivo de merge nao encontrado")
    return FileResponse(path=local_path, media_type="video/mp4",
                        filename=f"clipvox_{job_id}.mp4")


# ═══════════════════════════════════════════════════════════════
# BACKGROUND TASKS
# ═══════════════════════════════════════════════════════════════
def process_video_pipeline(job_id: str):
    job = jobs_db[job_id]
    try:
        update_job(job_id, status="processing", progress=5, current_step="plan")
        time.sleep(1)
        virtual_duration = get_virtual_duration(job["duration"])
        update_job(job_id, progress=10, current_step="analyzing")
        audio_metadata              = analyze_audio_cinematic(job["audio_path"], duration_override=virtual_duration)
        job["audio_duration"]       = audio_metadata["duration"]
        job["audio_bpm"]            = audio_metadata["bpm"]
        job["audio_key"]            = audio_metadata["key"]
        job["audio_energy_profile"] = audio_metadata["energy_profile"]
        update_job(job_id, progress=18)
        time.sleep(1)
        update_job(job_id, progress=22, current_step="calculating_scenes")
        scene_structure       = calculate_cinematic_scenes(audio_metadata, job["description"])
        print(get_scene_summary(scene_structure))
        job["total_scenes"]   = scene_structure["total_scenes"]
        job["total_segments"] = scene_structure["total_segments"]
        update_job(job_id, progress=28)
        update_job(job_id, progress=30, current_step="creative")

        # Pre-extrai vocals com StemSplit.io — 1x, reutilizado em todos os clips
        print("Extraindo vocals com StemSplit.io...")
        _preextract_vocals(job_id)

        print("Gerando conceito criativo com Claude API...")
        creative_concept = generate_creative_concept_with_prompts(
            audio_metadata, scene_structure, job["description"], job["style"]
        )
        job["creative_concept"] = creative_concept
        update_job(job_id, progress=58)
        time.sleep(2)
        update_job(job_id, progress=60, current_step="scenes")
        scenes_with_images = generate_scenes_batch(
            creative_concept["scenes"],
            style                = job["style"],
            aspect_ratio         = job["aspect_ratio"],
            resolution           = job["resolution"],
            reference_image_path = job.get("ref_image_path"),
            job_id               = job_id,
        )
        job["scenes"]    = scenes_with_images
        scenes_generated = sum(1 for s in scenes_with_images if s.get("success", False))
        update_job(job_id, progress=min(60 + int((scenes_generated / len(scenes_with_images)) * 20), 80))
        time.sleep(1)
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
        update_job(job_id, status="completed", progress=100, current_step="done",
                   output_file=f"video_{job_id}.mp4", videos_status="ready")
    except Exception as e:
        print(f"Erro no job {job_id}: {e}")
        import traceback; traceback.print_exc()
        update_job(job_id, status="failed", error_message=str(e))


def process_video_clips(job_id: str, mode: str = "std"):
    job = jobs_db.get(job_id)
    if not job:
        return
    try:
        scenes       = job.get("scenes", [])
        bpm          = job.get("audio_bpm", 120)
        aspect_ratio = job.get("aspect_ratio", "16:9")
        valid_scenes = [s for s in scenes if s.get("success", False) and s.get("image_url")]
        video_results = generate_videos_batch(
            scenes=valid_scenes, bpm=bpm, aspect_ratio=aspect_ratio, mode=mode, job_id=job_id,
        )
        success_count = sum(1 for r in video_results if r.get("success", False))
        print(f"Clipes gerados: {success_count}/{len(valid_scenes)}")
        jobs_db[job_id]["video_clips"]   = video_results
        jobs_db[job_id]["videos_status"] = "completed"
    except Exception as e:
        print(f"Erro ao gerar clipes: {e}")
        import traceback; traceback.print_exc()
        jobs_db[job_id]["videos_status"] = "failed"
        jobs_db[job_id]["videos_error"]  = str(e)


def process_lipsync(job_id: str, face_source: str, audio_path: str, model: str):
    """Aplica lip sync em CADA clipe individualmente."""
    job = jobs_db.get(job_id, {})
    video_clips      = job.get("video_clips") or []
    successful_clips = sorted(
        [c for c in video_clips if c.get("success") and c.get("video_url")],
        key=lambda x: x.get("scene_number", 0)
    )

    if not successful_clips:
        jobs_db[job_id]["lipsync_status"] = "failed"
        jobs_db[job_id]["lipsync_error"]  = "Nenhum video_clip disponivel."
        return

    # ✅ FIX: aguarda vocals_path ser definido antes de iniciar o loop
    # Evita race condition onde Scene 1 começa antes do StemSplit terminar
    vocals_path = jobs_db.get(job_id, {}).get("vocals_path")
    if not vocals_path:
        print("   ⏳ Aguardando StemSplit finalizar extração de vocals...")
        for _ in range(18):  # até 3 minutos (18 x 10s)
            time.sleep(10)
            vocals_path = jobs_db.get(job_id, {}).get("vocals_path")
            if vocals_path:
                print(f"   ✅ Vocals prontos: {os.path.basename(vocals_path)}")
                break
        else:
            print("   ⚠️ Timeout aguardando vocals — lip sync usará áudio original")

    total         = len(successful_clips)
    lipsync_clips = []
    success_count = 0

    for i, clip in enumerate(successful_clips):
        scene_num      = clip.get("scene_number", i + 1)
        face_video_url = clip.get("kling_url") or clip.get("video_url")
        clip_job_id    = f"{job_id}_scene{scene_num:03d}"

        result = generate_lipsync(
            face_source=face_video_url,
            audio_source=audio_path,
            job_id=clip_job_id,
            model=model,
            preextracted_vocals=vocals_path,  # ✅ mesmo valor para TODOS os clips
        )

        if result["success"]:
            success_count += 1
            lipsync_clips.append({
                "success": True, "scene_number": scene_num,
                "video_url": result["video_url"], "original_url": face_video_url,
            })
        else:
            lipsync_clips.append({
                "success": True, "scene_number": scene_num,
                "video_url": clip.get("video_url"), "original_url": face_video_url,
                "lipsync_error": result.get("error"),
            })

    jobs_db[job_id]["lipsync_clips"]  = lipsync_clips
    jobs_db[job_id]["lipsync_status"] = "completed"
    first_ok = next((c for c in lipsync_clips if c.get("success")), None)
    if first_ok:
        jobs_db[job_id]["lipsync_url"] = first_ok["video_url"]
    print(f"Lip sync: {success_count}/{total} clipes sincronizados")


def process_merge(job_id: str):
    """Usa lipsync_clips se disponivel, senao video_clips originais."""
    job = jobs_db.get(job_id)
    if not job:
        return
    try:
        lipsync_clips = job.get("lipsync_clips")
        clips         = lipsync_clips if lipsync_clips else job.get("video_clips", [])
        clips_source  = "lip sync" if lipsync_clips else "originais"

        successful = sorted(
            [c for c in clips if c.get("success") and c.get("video_url")],
            key=lambda x: x.get("scene_number", 0)
        )
        video_urls = [c["video_url"] for c in successful]
        audio_path = job.get("audio_path")

        result = merge_clips_with_audio(video_urls=video_urls, audio_path=audio_path, job_id=job_id)

        if result["success"]:
            jobs_db[job_id]["merge_status"] = "completed"
            if result.get("output_url"):
                jobs_db[job_id]["merge_url"] = result["output_url"]
            else:
                backend_url  = os.getenv("BACKEND_URL", "https://clipvox-backend.onrender.com")
                jobs_db[job_id]["merge_url"] = f"{backend_url}/api/videos/download/{job_id}"
        else:
            jobs_db[job_id]["merge_status"] = "failed"
            jobs_db[job_id]["merge_error"]  = result.get("error")
    except Exception as e:
        import traceback; traceback.print_exc()
        jobs_db[job_id]["merge_status"] = "failed"
        jobs_db[job_id]["merge_error"]  = str(e)


def _preextract_vocals(job_id: str):
    """
    Extrai vocals com StemSplit.io — substitui LALAL.AI (que exigia premium).
    Roda 1x por job, resultado reutilizado em todos os clips de lip sync.
    """
    try:
        job        = jobs_db.get(job_id, {})
        audio_path = job.get("audio_path")
        if not audio_path or not os.path.exists(audio_path):
            return
        from services.stemsplit_vocals import extract_vocals
        vocals_path = extract_vocals(audio_path, job_id)
        if vocals_path:
            jobs_db[job_id]["vocals_path"] = vocals_path
            print(f"Vocals pre-extraidos (StemSplit): {os.path.basename(vocals_path)}")
        else:
            print("StemSplit falhou — lip sync usara audio original")
    except Exception as e:
        print(f"Erro na pre-extracao de vocals: {e}")


def update_job(job_id: str, **kwargs):
    if job_id in jobs_db:
        jobs_db[job_id].update(kwargs)
