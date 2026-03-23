from fastapi import APIRouter, UploadFile, File, Form, HTTPException, BackgroundTasks
from fastapi.responses import JSONResponse, FileResponse
from typing import Optional
import os
import uuid
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from config import UPLOAD_DIR, CREDITS_PER_VIDEO
from services.audio_analysis import analyze_audio_cinematic
from services.scene_calculator import calculate_cinematic_scenes, get_scene_summary
from services.ai_concept import generate_creative_concept_with_prompts
from services.video_generation import generate_scenes_batch
from services.kling_video import generate_videos_batch
from services.merge_video import merge_clips_with_audio, MERGE_OUTPUT_DIR
from services.kling_lipsync import generate_lipsync

router  = APIRouter()

from services.job_store import save_job, load_job, load_recent_jobs
jobs_db: dict = {}

def _init_jobs_db():
    global jobs_db
    restored = load_recent_jobs(limit=100)
    jobs_db.update(restored)

try:
    _init_jobs_db()
except Exception as _e:
    print(f"⚠️ Supabase startup load error: {_e}")

try:
    from services.video_generation import set_jobs_cache
    set_jobs_cache(jobs_db)
except Exception as _e:
    print(f"⚠️ set_jobs_cache error: {_e}")


def get_virtual_duration(duration: str) -> int:
    if duration == "full":
        return None
    try:
        return int(duration)
    except Exception:
        return None


def _map_lipsync_failure(result: dict):
    raw = (result.get("raw_error") or result.get("error") or "") if isinstance(result, dict) else ""
    etype = result.get("error_type") if isinstance(result, dict) else None
    raw_l = raw.lower()

    if not etype:
        if "no face" in raw_l or "609" in raw or "identify failed" in raw_l:
            etype = "no_face"
        elif "proxy" in raw_l or "proxyconnect" in raw_l:
            etype = "proxy"
        elif "service busy" in raw_l or "500 service" in raw_l:
            etype = "busy"
        elif "too large" in raw_l or "10mb" in raw_l or "file size" in raw_l:
            etype = "too_large"
        elif "404 not found" in raw_l and ("deleted" in raw_l or "content violation" in raw_l):
            etype = "deleted"
        elif "timeout" in raw_l or "timed out" in raw_l or "read timed out" in raw_l:
            etype = "timeout"
        elif "cancelled" in raw_l or "cancelado" in raw_l:
            etype = "cancelled"
        else:
            etype = "unknown"

    if etype == "no_face":
        msg = "Sem rosto detectado — regenere a imagem com rosto frontal"
    elif etype == "proxy":
        msg = "Erro de conexão — tente novamente mais tarde"
    elif etype == "busy":
        msg = "Servidor sobrecarregado — tente mais tarde"
    elif etype == "too_large":
        msg = "Vídeo acima do limite do Kling — regenere esta cena"
    elif etype == "deleted":
        msg = "Task removida pelo Kling — regenere esta cena"
    elif etype == "timeout":
        msg = "Tempo de resposta excedido — tente regenerar"
    elif etype == "cancelled":
        msg = "Cancelado pelo usuário"
    else:
        msg = "Falha no lip sync — tente novamente"

    return msg, etype, raw


@router.post("/generate")
async def generate_video(
    audio:        UploadFile      = File(...),
    description:  str             = Form(""),
    style:        str             = Form("realistic"),
    duration:     str             = Form("full"),
    aspect_ratio: str             = Form("16:9"),
    resolution:   str             = Form("720p"),
    ref_image:    Optional[UploadFile] = File(None),
    ref_image_2:  Optional[UploadFile] = File(None),
    ref_image_3:  Optional[UploadFile] = File(None),
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

    ref_image_path  = None
    ref_image_paths = []
    for i, ri in enumerate([ref_image, ref_image_2, ref_image_3], start=1):
        if ri and ri.filename:
            rp = os.path.join(UPLOAD_DIR, f"{job_id}_ref{i}_{ri.filename}")
            with open(rp, "wb") as f:
                f.write(await ri.read())
            ref_image_paths.append(rp)
    if ref_image_paths:
        ref_image_path = ref_image_paths[0]

    jobs_db[job_id] = {
        "id": job_id, "status": "pending", "progress": 0, "current_step": "plan",
        "audio_filename": audio.filename, "audio_path": audio_path,
        "description": description, "style": style, "duration": duration,
        "aspect_ratio": aspect_ratio, "resolution": resolution,
        "ref_image_path": ref_image_path, "ref_image_paths": ref_image_paths,
        "created_at": time.time(), "video_clips": None, "videos_status": "pending",
        "lipsync_status": None, "lipsync_url": None, "lipsync_clips": None,
        "vocals_path": None, "merge_status": None, "merge_url": None,
    }
    background_tasks.add_task(process_video_pipeline, job_id)
    try:
        save_job(job_id, jobs_db[job_id])
    except Exception as _e:
        print(f"⚠️ save_job (create) error: {_e}")

    return {
        "job_id": job_id, "status": "processing", "message": "Video generation started",
        "config": {"duration": duration, "aspect_ratio": aspect_ratio,
                   "resolution": resolution, "style": style,
                   "has_reference_image": ref_image is not None}
    }


@router.get("/status/{job_id}")
async def get_job_status(job_id: str):
    if job_id not in jobs_db:
        recovered = load_job(job_id)
        if recovered:
            jobs_db[job_id] = recovered
        else:
            raise HTTPException(404, "Job not found")
    job = jobs_db[job_id]
    return {
        "id": job["id"], "status": job["status"], "progress": job["progress"],
        "current_step": job.get("current_step"), "audio_duration": job.get("audio_duration"),
        "audio_bpm": job.get("audio_bpm"), "audio_key": job.get("audio_key"),
        "creative_concept": job.get("creative_concept"), "scenes": job.get("scenes"),
        "segments": job.get("segments"), "output_file": job.get("output_file"),
        "error_message": job.get("error_message"), "video_clips": job.get("video_clips"),
        "videos_status": job.get("videos_status"), "lipsync_status": job.get("lipsync_status"),
        "lipsync_url": job.get("lipsync_url"), "lipsync_clips": job.get("lipsync_clips"),
        "merge_status": job.get("merge_status"), "merge_url": job.get("merge_url"),
        "cancelled": job.get("cancelled", False),
        "config": {
            "duration": job.get("duration"), "aspect_ratio": job.get("aspect_ratio"),
            "resolution": job.get("resolution"), "style": job.get("style"),
            "has_reference_image": job.get("ref_image_path") is not None,
        }
    }


@router.post("/generate-clips/{job_id}")
async def generate_video_clips(job_id: str, background_tasks: BackgroundTasks, mode: str = "std"):
    if job_id not in jobs_db:
        recovered = load_job(job_id)
        if recovered:
            jobs_db[job_id] = recovered
        else:
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
        "job_id": job_id, "status": "processing",
        "message": f"Gerando {total_scenes} clipes de video com Kling AI...",
        "estimated_cost": f"~${total_scenes * (0.125 if mode == 'std' else 0.25):.2f}",
        "mode": mode,
    }


@router.post("/regen-scene/{job_id}/{scene_number}")
async def regen_scene_image(
    job_id: str, scene_number: int,
    background_tasks: BackgroundTasks, prompt: str = Form(""),
):
    if job_id not in jobs_db:
        recovered = load_job(job_id)
        if recovered:
            jobs_db[job_id] = recovered
        else:
            raise HTTPException(404, "Job not found")
    job    = jobs_db[job_id]
    scenes = job.get("scenes") or []
    scene  = next((s for s in scenes if s.get("scene_number") == scene_number), None)
    if not scene:
        raise HTTPException(404, f"Cena {scene_number} não encontrada")
    final_prompt = prompt.strip() or scene.get("prompt", "")
    if not final_prompt:
        raise HTTPException(400, "Prompt não encontrado para esta cena")
    background_tasks.add_task(process_regen_scene, job_id=job_id,
                               scene_number=scene_number, prompt=final_prompt)
    return {"job_id": job_id, "scene_number": scene_number, "status": "regenerating",
            "message": f"Regenerando cena {scene_number}..."}


@router.post("/regen-video/{job_id}/{scene_number}")
async def regen_video_clip(
    job_id: str, scene_number: int,
    background_tasks: BackgroundTasks, mode: str = Form("std"),
):
    if job_id not in jobs_db:
        recovered = load_job(job_id)
        if recovered:
            jobs_db[job_id] = recovered
        else:
            raise HTTPException(404, "Job not found")
    job    = jobs_db[job_id]
    scenes = job.get("scenes") or []
    scene  = next((s for s in scenes if s.get("scene_number") == scene_number), None)
    if not scene or not scene.get("image_url"):
        raise HTTPException(404, f"Cena {scene_number} sem imagem disponível")
    background_tasks.add_task(process_regen_video, job_id=job_id,
                               scene_number=scene_number, scene=scene, mode=mode)
    return {"job_id": job_id, "scene_number": scene_number, "status": "regenerating",
            "message": f"Regenerando vídeo da cena {scene_number}..."}


# ══════════════════════════════════════════════════════
# ✅ NOVO: Refazer lip sync de UMA cena específica
# ══════════════════════════════════════════════════════
@router.post("/regen-lipsync/{job_id}/{scene_number}")
async def regen_lipsync_clip(
    job_id: str, scene_number: int,
    background_tasks: BackgroundTasks,
    model: str = Form("kling"),
):
    """Refaz lip sync de UMA cena específica que falhou — sem reprocessar as outras."""
    if job_id not in jobs_db:
        recovered = load_job(job_id)
        if recovered:
            jobs_db[job_id] = recovered
        else:
            raise HTTPException(404, "Job not found")
    job = jobs_db[job_id]

    # Encontra o clipe de vídeo original (precisa do task_id para origin_task_id)
    video_clips = job.get("video_clips") or []
    clip = next((c for c in video_clips if c.get("scene_number") == scene_number), None)
    if not clip or not clip.get("video_url"):
        raise HTTPException(404, f"Clipe da cena {scene_number} não encontrado")

    # Verifica se áudio ainda existe no servidor (Render /tmp é volátil)
    audio_path = job.get("audio_path")
    if not audio_path or not os.path.exists(audio_path):
        raise HTTPException(
            400,
            "Áudio não encontrado no servidor (Render reiniciou). "
            "Use o painel de Lip Sync para reenviar o áudio."
        )

    vocals_path = job.get("vocals_path")

    # Marca a cena como lipsync_regenerating nos lipsync_clips
    lipsync_clips = list(jobs_db[job_id].get("lipsync_clips") or [])
    found = any(c.get("scene_number") == scene_number for c in lipsync_clips)
    if found:
        for c in lipsync_clips:
            if c.get("scene_number") == scene_number:
                c["lipsync_regenerating"] = True
    else:
        lipsync_clips.append({
            "scene_number": scene_number, "success": True,
            "video_url": clip.get("video_url"), "lipsync_regenerating": True,
        })
    jobs_db[job_id]["lipsync_clips"] = sorted(lipsync_clips, key=lambda x: x.get("scene_number", 0))
    save_job(job_id, jobs_db[job_id])

    background_tasks.add_task(
        process_regen_lipsync,
        job_id=job_id, scene_number=scene_number, clip=clip,
        audio_path=audio_path, vocals_path=vocals_path, model=model,
    )
    return {"job_id": job_id, "scene_number": scene_number,
            "status": "processing", "message": f"Refazendo lip sync da cena {scene_number}..."}


@router.post("/cancel/{job_id}")
async def cancel_job(job_id: str):
    if job_id not in jobs_db:
        recovered = load_job(job_id)
        if recovered:
            jobs_db[job_id] = recovered
        else:
            raise HTTPException(404, "Job not found")
    jobs_db[job_id]["cancelled"] = True
    update_job(job_id, cancelled=True)
    return {"job_id": job_id, "status": "cancelled", "message": "Job cancelado"}


@router.post("/retry-clips/{job_id}")
async def retry_failed_clips(job_id: str, background_tasks: BackgroundTasks, mode: str = "std"):
    if job_id not in jobs_db:
        recovered = load_job(job_id)
        if recovered:
            jobs_db[job_id] = recovered
        else:
            raise HTTPException(404, "Job not found")
    job = jobs_db[job_id]
    video_clips  = job.get("video_clips") or []
    scenes_all   = job.get("scenes") or []
    failed_nums  = {c["scene_number"] for c in video_clips if not c.get("success") or not c.get("video_url")}
    if not failed_nums:
        return {"message": "Nenhuma cena com falha encontrada", "job_id": job_id}
    failed_scenes = [s for s in scenes_all if s.get("scene_number") in failed_nums and s.get("image_url")]
    if not failed_scenes:
        raise HTTPException(400, "Cenas com falha não têm imagens disponíveis para regenerar")
    if job.get("videos_status") == "retrying":
        return {"message": "Retry já em andamento", "job_id": job_id}
    jobs_db[job_id]["videos_status"] = "retrying"
    background_tasks.add_task(process_retry_clips, job_id=job_id, failed_scenes=failed_scenes, mode=mode)
    return {"job_id": job_id, "status": "retrying",
            "message": f"Regenerando {len(failed_scenes)} cenas com falha...",
            "failed_scenes": sorted(failed_nums), "mode": mode}


@router.post("/lipsync/{job_id}")
async def generate_lipsync_video(
    job_id: str, background_tasks: BackgroundTasks,
    face_image: Optional[UploadFile] = File(None),
    audio:      Optional[UploadFile] = File(None),
    face_url:   str = Form(""), model: str = Form("kling"),
):
    if job_id not in jobs_db:
        recovered = load_job(job_id)
        if recovered:
            jobs_db[job_id] = recovered
        else:
            raise HTTPException(404, "Job not found")
    job = jobs_db[job_id]

    if audio and audio.filename:
        audio_filename = f"{job_id}_{audio.filename}"
        audio_path     = os.path.join(UPLOAD_DIR, audio_filename)
        with open(audio_path, "wb") as f:
            f.write(await audio.read())
        jobs_db[job_id]["audio_path"]  = audio_path
        jobs_db[job_id]["vocals_path"] = None
        update_job(job_id, audio_path=audio_path, vocals_path=None)
    else:
        audio_path = job.get("audio_path")
        if not audio_path or not os.path.exists(audio_path):
            raise HTTPException(400, "Audio do job nao encontrado")

    face_source = None
    if face_image:
        face_path = os.path.join(UPLOAD_DIR, f"{job_id}_lipsync_face_{face_image.filename}")
        with open(face_path, "wb") as f:
            f.write(await face_image.read())
        face_source = face_path
    elif face_url:
        face_source = face_url
    elif job.get("ref_image_path") and os.path.exists(job["ref_image_path"]):
        face_source = job["ref_image_path"]
    else:
        scenes = job.get("scenes") or []
        first_scene_url = next(
            (s.get("image_url") or s.get("r2_url") for s in scenes if s.get("image_url") or s.get("r2_url")), None
        )
        if first_scene_url:
            face_source = first_scene_url
        else:
            raise HTTPException(400, "Nenhuma imagem do personagem encontrada.")

    if job.get("lipsync_status") == "processing":
        return {"message": "Lip sync ja em andamento", "job_id": job_id}

    video_clips = job.get("video_clips", [])
    successful  = [c for c in video_clips if c.get("success") and c.get("video_url")]

    jobs_db[job_id]["lipsync_status"] = "processing"
    jobs_db[job_id]["lipsync_url"]    = None
    jobs_db[job_id]["lipsync_clips"]  = None

    background_tasks.add_task(_preextract_and_lipsync, job_id=job_id,
                               face_source=face_source, audio_path=audio_path, model=model)
    return {"job_id": job_id, "status": "processing",
            "message": f"Lip sync iniciado em {len(successful)} clipe(s)",
            "total_clips": len(successful), "model": model}


@router.post("/merge/{job_id}")
async def merge_final_video(job_id: str, background_tasks: BackgroundTasks):
    if job_id not in jobs_db:
        recovered = load_job(job_id)
        if recovered:
            jobs_db[job_id] = recovered
        else:
            raise HTTPException(404, "Job not found")
    job = jobs_db[job_id]
    videos_ok  = job.get("videos_status") == "completed"
    lipsync_ok = job.get("lipsync_status") == "completed"
    if not videos_ok and not lipsync_ok:
        raise HTTPException(400, "Clipes ainda nao gerados.")
    clips_to_use = job.get("lipsync_clips") or job.get("video_clips", [])
    successful   = [c for c in clips_to_use if c.get("success") and c.get("video_url")]
    if not successful:
        raise HTTPException(400, "Nenhum clipe disponivel para merge")
    if job.get("merge_status") == "processing":
        return {"message": "Merge ja em andamento", "job_id": job_id}
    jobs_db[job_id]["merge_status"] = "processing"
    jobs_db[job_id]["merge_url"]    = None
    background_tasks.add_task(process_merge, job_id)
    return {"job_id": job_id, "status": "processing",
            "message": f"Merge de {len(successful)} clipes iniciado"}


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
        scene_structure     = calculate_cinematic_scenes(audio_metadata, job["description"])
        job["total_scenes"] = scene_structure["total_scenes"]
        update_job(job_id, progress=28)
        update_job(job_id, progress=30, current_step="creative")

        print("Extraindo vocals com StemSplit.io...")
        _preextract_vocals(job_id)

        creative_concept = generate_creative_concept_with_prompts(
            audio_metadata, scene_structure, job["description"], job["style"]
        )
        job["creative_concept"] = creative_concept
        update_job(job_id, progress=58)
        time.sleep(2)
        update_job(job_id, progress=60, current_step="scenes")
        scenes_with_images = generate_scenes_batch(
            creative_concept["scenes"],
            style=job["style"], aspect_ratio=job["aspect_ratio"],
            resolution=job["resolution"], reference_image_path=job.get("ref_image_path"),
            reference_image_paths=job.get("ref_image_paths") or [], job_id=job_id,
        )
        job["scenes"] = scenes_with_images
        scenes_generated = sum(1 for s in scenes_with_images if s.get("success", False))
        jobs_db[job_id]["scenes"] = scenes_with_images

        # ✅ Normaliza campo 'prompt' — garante que o frontend sempre encontre
        # independente do nome usado internamente pelo ai_concept/video_generation
        for scene in jobs_db[job_id]["scenes"]:
            if not scene.get("prompt"):
                scene["prompt"] = (
                    scene.get("visual_prompt") or
                    scene.get("image_prompt") or
                    scene.get("prompt_used") or
                    scene.get("visual_description") or
                    scene.get("scene_description") or
                    scene.get("description") or
                    ""
                )

        try:
            save_job(job_id, jobs_db[job_id])
        except Exception as _e:
            print(f"⚠️ Save cenas falhou: {_e}")
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
    if jobs_db.get(job_id, {}).get("cancelled"):
        jobs_db[job_id]["videos_status"] = "cancelled"
        save_job(job_id, jobs_db[job_id])
        return
    try:
        scenes       = job.get("scenes", [])
        valid_scenes = [s for s in scenes if s.get("success", False) and s.get("image_url")]
        video_results = generate_videos_batch(
            scenes=valid_scenes, bpm=job.get("audio_bpm", 120),
            aspect_ratio=job.get("aspect_ratio", "16:9"),
            mode=mode, job_id=job_id, version="2.1",
        )
        jobs_db[job_id]["video_clips"]   = video_results
        jobs_db[job_id]["videos_status"] = "completed"
        save_job(job_id, jobs_db[job_id])
    except Exception as e:
        import traceback; traceback.print_exc()
        jobs_db[job_id]["videos_status"] = "failed"
        jobs_db[job_id]["videos_error"]  = str(e)
        save_job(job_id, jobs_db[job_id])


def process_retry_clips(job_id: str, failed_scenes: list, mode: str = "std"):
    job = jobs_db.get(job_id)
    if not job:
        return
    try:
        if jobs_db.get(job_id, {}).get("cancelled"):
            jobs_db[job_id]["videos_status"] = "cancelled"
            return
        new_results = generate_videos_batch(
            scenes=failed_scenes, bpm=job.get("audio_bpm", 120),
            aspect_ratio=job.get("aspect_ratio", "16:9"),
            mode=mode, job_id=job_id, version="2.1",
        )
        existing = {c["scene_number"]: c for c in (job.get("video_clips") or [])}
        for r in new_results:
            existing[r["scene_number"]] = r
        merged = sorted(existing.values(), key=lambda x: x.get("scene_number", 0))
        jobs_db[job_id]["video_clips"]   = merged
        jobs_db[job_id]["videos_status"] = "completed"
        save_job(job_id, jobs_db[job_id])
    except Exception as e:
        import traceback; traceback.print_exc()
        jobs_db[job_id]["videos_status"] = "failed"
        save_job(job_id, jobs_db[job_id])


def process_regen_scene(job_id: str, scene_number: int, prompt: str):
    try:
        job = jobs_db.get(job_id, {})
        if job.get("cancelled"):
            return
        from services.video_generation import generate_scene_image
        scenes = jobs_db[job_id].get("scenes") or []
        for s in scenes:
            if s.get("scene_number") == scene_number:
                s["regenerating"] = True
        jobs_db[job_id]["scenes"] = scenes
        save_job(job_id, jobs_db[job_id])

        result = generate_scene_image(
            prompt=prompt, scene_number=scene_number,
            style=job.get("style", "realistic"), aspect_ratio=job.get("aspect_ratio", "16:9"),
            resolution=job.get("resolution", "720p"), reference_imgbb_url=None, job_id=job_id,
        )
        scenes = jobs_db[job_id].get("scenes") or []
        for i, s in enumerate(scenes):
            if s.get("scene_number") == scene_number:
                result["prompt"] = prompt
                result["regenerating"] = False
                scenes[i] = result
                break
        jobs_db[job_id]["scenes"] = scenes
        save_job(job_id, jobs_db[job_id])
    except Exception as e:
        import traceback; traceback.print_exc()
        scenes = jobs_db.get(job_id, {}).get("scenes") or []
        for s in scenes:
            if s.get("scene_number") == scene_number:
                s["regenerating"] = False
        save_job(job_id, jobs_db[job_id])


def process_regen_video(job_id: str, scene_number: int, scene: dict, mode: str):
    try:
        job = jobs_db.get(job_id, {})
        if job.get("cancelled"):
            return
        from services.kling_video import generate_video_clip
        clips = jobs_db[job_id].get("video_clips") or []
        for c in clips:
            if c.get("scene_number") == scene_number:
                c["regenerating"] = True
        jobs_db[job_id]["video_clips"] = clips
        save_job(job_id, jobs_db[job_id])

        result = generate_video_clip(
            scene=scene, bpm=job.get("audio_bpm", 120),
            aspect_ratio=job.get("aspect_ratio", "16:9"), mode=mode, job_id=job_id
        )
        clips = jobs_db[job_id].get("video_clips") or []
        found = False
        for i, c in enumerate(clips):
            if c.get("scene_number") == scene_number:
                result["regenerating"] = False
                clips[i] = result
                found = True
                break
        if not found:
            result["regenerating"] = False
            clips.append(result)
        jobs_db[job_id]["video_clips"] = sorted(clips, key=lambda x: x.get("scene_number", 0))
        save_job(job_id, jobs_db[job_id])
    except Exception as e:
        import traceback; traceback.print_exc()
        clips = jobs_db.get(job_id, {}).get("video_clips") or []
        for c in clips:
            if c.get("scene_number") == scene_number:
                c["regenerating"] = False
        save_job(job_id, jobs_db[job_id])


# ══════════════════════════════════════════════════════
# ✅ NOVO: Refaz lip sync de UMA cena específica
# ══════════════════════════════════════════════════════
def process_regen_lipsync(job_id: str, scene_number: int, clip: dict,
                           audio_path: str, vocals_path: str, model: str):
    """Refaz lip sync de uma única cena e atualiza lipsync_clips."""
    try:
        face_video_url = clip.get("kling_url") or clip.get("video_url")
        origin_task_id = clip.get("task_id", "")
        clip_job_id    = f"{job_id}_scene{scene_number:03d}"
        print(f"🎤 Refazendo lip sync cena {scene_number} — job {job_id[:8]}...")

        # Se vocals não existe mais no disco, tenta extrair novamente
        if not vocals_path or not os.path.exists(str(vocals_path)):
            print(f"   ⚠️ vocals_path ausente — extraindo com StemSplit...")
            _preextract_vocals(job_id)
            vocals_path = jobs_db.get(job_id, {}).get("vocals_path")

        result = generate_lipsync(
            face_source=face_video_url, audio_source=audio_path,
            job_id=clip_job_id, model=model,
            preextracted_vocals=vocals_path, origin_task_id=origin_task_id,
        )

        if result["success"]:
            new_clip = {
                "success": True, "scene_number": scene_number,
                "video_url": result["video_url"], "original_url": face_video_url,
                "lipsync_regenerating": False,
                "lipsync_error": None, "lipsync_error_type": None,
            }
            print(f"   ✅ Cena {scene_number} sincronizada com sucesso")
        else:
            msg, etype, raw = _map_lipsync_failure(result)
            new_clip = {
                "success": True, "scene_number": scene_number,
                "video_url": clip.get("video_url"), "original_url": face_video_url,
                "lipsync_error": msg, "lipsync_error_type": etype,
                "lipsync_regenerating": False,
            }
            print(f"   ❌ Cena {scene_number} falhou novamente ({etype})")

        lipsync_clips = list(jobs_db[job_id].get("lipsync_clips") or [])
        updated = False
        for i, c in enumerate(lipsync_clips):
            if c.get("scene_number") == scene_number:
                lipsync_clips[i] = new_clip
                updated = True
                break
        if not updated:
            lipsync_clips.append(new_clip)

        jobs_db[job_id]["lipsync_clips"] = sorted(lipsync_clips, key=lambda x: x.get("scene_number", 0))
        save_job(job_id, jobs_db[job_id])

    except Exception as e:
        import traceback; traceback.print_exc()
        lipsync_clips = list(jobs_db.get(job_id, {}).get("lipsync_clips") or [])
        for c in lipsync_clips:
            if c.get("scene_number") == scene_number:
                c["lipsync_regenerating"] = False
                c["lipsync_error"] = "Erro inesperado — tente novamente"
        jobs_db[job_id]["lipsync_clips"] = lipsync_clips
        save_job(job_id, jobs_db[job_id])


def _preextract_and_lipsync(job_id: str, face_source: str, audio_path: str, model: str):
    if jobs_db.get(job_id, {}).get("cancelled"):
        return
    _preextract_vocals(job_id)
    process_lipsync(job_id=job_id, face_source=face_source, audio_path=audio_path, model=model)


def process_lipsync(job_id: str, face_source: str, audio_path: str, model: str):
    job = jobs_db.get(job_id, {})
    video_clips = job.get("video_clips") or []
    successful_clips = sorted(
        [c for c in video_clips if c.get("success") and c.get("video_url")],
        key=lambda x: x.get("scene_number", 0)
    )
    if not successful_clips:
        jobs_db[job_id]["lipsync_status"] = "failed"
        jobs_db[job_id]["lipsync_error"]  = "Nenhum video_clip disponivel."
        return
    if jobs_db.get(job_id, {}).get("cancelled"):
        jobs_db[job_id]["lipsync_status"] = "cancelled"
        save_job(job_id, jobs_db[job_id])
        return

    vocals_path = jobs_db.get(job_id, {}).get("vocals_path")
    if not vocals_path:
        for _ in range(18):
            time.sleep(10)
            vocals_path = jobs_db.get(job_id, {}).get("vocals_path")
            if vocals_path:
                break

    total = len(successful_clips)

    def _process_clip(args):
        i, clip = args
        scene_num      = clip.get("scene_number", i + 1)
        face_video_url = clip.get("kling_url") or clip.get("video_url")
        clip_job_id    = f"{job_id}_scene{scene_num:03d}"
        if jobs_db.get(job_id, {}).get("cancelled"):
            return {"success": False, "scene_number": scene_num,
                    "video_url": clip.get("video_url"), "lipsync_error": "cancelled"}
        origin_task_id = clip.get("task_id", "")
        print(f"🎤 Lip sync clipe {scene_num}/{total}...")
        result = generate_lipsync(
            face_source=face_video_url, audio_source=audio_path,
            job_id=clip_job_id, model=model,
            preextracted_vocals=vocals_path, origin_task_id=origin_task_id,
        )
        if result["success"]:
            return {"success": True, "scene_number": scene_num,
                    "video_url": result["video_url"], "original_url": face_video_url}
        msg, etype, raw = _map_lipsync_failure(result)
        if etype == "no_face":
            msg = "Sem rosto detectado — regenere a imagem"
        elif etype == "proxy":
            msg = "Erro de conexão — tente regenerar o lip sync desta cena"
        elif etype == "busy":
            msg = "Servidor sobrecarregado — tente regenerar esta cena"
        elif etype == "too_large":
            msg = "Vídeo acima do limite do Kling — regenere esta cena"
        elif etype == "deleted":
            msg = "Task removida pelo Kling — regenere esta cena"
        elif etype == "timeout":
            msg = "Tempo de resposta excedido — tente regenerar"
        elif etype == "cancelled":
            msg = "Cancelado pelo usuário"
        else:
            msg = "Falha no lip sync — tente regenerar"
        return {"success": True, "scene_number": scene_num,
                "video_url": clip.get("video_url"), "original_url": face_video_url,
                "lipsync_error": msg, "lipsync_error_type": etype}

    results_map = {}
    with ThreadPoolExecutor(max_workers=1) as executor:
        futures = {executor.submit(_process_clip, (i, c)): i for i, c in enumerate(successful_clips)}
        for future in as_completed(futures):
            r = future.result()
            results_map[r["scene_number"]] = r

    lipsync_clips = [results_map[k] for k in sorted(results_map)]
    success_count = sum(1 for c in lipsync_clips if not c.get("lipsync_error"))
    jobs_db[job_id]["lipsync_clips"]  = lipsync_clips
    jobs_db[job_id]["lipsync_status"] = "completed"
    first_ok = next((c for c in lipsync_clips if c.get("success")), None)
    if first_ok:
        jobs_db[job_id]["lipsync_url"] = first_ok["video_url"]
    print(f"Lip sync: {success_count}/{total} clipes sincronizados")
    save_job(job_id, jobs_db[job_id])


def process_merge(job_id: str):
    job = jobs_db.get(job_id)
    if not job:
        return
    try:
        clips    = job.get("lipsync_clips") or job.get("video_clips", [])
        success  = sorted([c for c in clips if c.get("success") and c.get("video_url")],
                          key=lambda x: x.get("scene_number", 0))
        result   = merge_clips_with_audio(
            video_urls=[c["video_url"] for c in success],
            audio_path=job.get("audio_path"), job_id=job_id
        )
        if result["success"]:
            jobs_db[job_id]["merge_status"] = "completed"
            jobs_db[job_id]["merge_url"] = result.get("output_url") or \
                f"{os.getenv('BACKEND_URL','https://clipvox-backend.onrender.com')}/api/videos/download/{job_id}"
        else:
            jobs_db[job_id]["merge_status"] = "failed"
            jobs_db[job_id]["merge_error"]  = result.get("error")
        save_job(job_id, jobs_db[job_id])
    except Exception as e:
        import traceback; traceback.print_exc()
        jobs_db[job_id]["merge_status"] = "failed"
        jobs_db[job_id]["merge_error"]  = str(e)


def _preextract_vocals(job_id: str):
    try:
        job = jobs_db.get(job_id, {})
        if job.get("cancelled"):
            return
        audio_path = job.get("audio_path")
        if not audio_path or not os.path.exists(audio_path):
            return
        duration_str = job.get("duration", "full")
        if duration_str and duration_str != "full":
            try:
                duration_sec = int(duration_str)
                trimmed_path = audio_path.rsplit(".", 1)[0] + f"_trim{duration_sec}s.mp3"
                import subprocess
                r = subprocess.run([
                    "ffmpeg", "-y", "-i", audio_path, "-t", str(duration_sec),
                    "-acodec", "libmp3lame", "-ab", "192k", trimmed_path
                ], capture_output=True, text=True, timeout=60)
                if r.returncode == 0 and os.path.exists(trimmed_path):
                    audio_path = trimmed_path
            except Exception as te:
                print(f"⚠️ Erro ao trimar áudio: {te}")
        from services.stemsplit_vocals import extract_vocals
        vocals_path = extract_vocals(audio_path, job_id)
        if vocals_path:
            jobs_db[job_id]["vocals_path"] = vocals_path
        else:
            print("StemSplit falhou — lip sync usara audio original")
    except Exception as e:
        print(f"Erro na pre-extracao de vocals: {e}")


def update_job(job_id: str, **kwargs):
    if job_id in jobs_db:
        jobs_db[job_id].update(kwargs)
        try:
            save_job(job_id, jobs_db[job_id])
        except Exception as _e:
            print(f"⚠️ save_job error: {_e}")
