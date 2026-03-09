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
        print(f"⏱️ Virtual trim: Using {duration_seconds}s for scene calculations")
        return duration_seconds
    except Exception as e:
        print(f"❌ Error parsing duration: {e}")
        return None


# ═══════════════════════════════════════════════════════════════
# POST /generate
# ═══════════════════════════════════════════════════════════════
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
            raise HTTPException(400, f"Formato não suportado: {audio.content_type}")

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
        print(f"✅ Imagem de referência salva: {os.path.basename(ref_image_path)}")

    jobs_db[job_id] = {
        "id":               job_id,
        "status":           "pending",
        "progress":         0,
        "current_step":     "plan",
        "audio_filename":   audio.filename,
        "audio_path":       audio_path,
        "description":      description,
        "style":            style,
        "duration":         duration,
        "aspect_ratio":     aspect_ratio,
        "resolution":       resolution,
        "ref_image_path":   ref_image_path,
        "created_at":       time.time(),
        "video_clips":      None,
        "videos_status":    "pending",
        "lipsync_status":   None,
        "lipsync_url":      None,
        "lipsync_clips":    None,   # ✅ lip sync por clipe
        "merge_status":     None,
        "merge_url":        None,
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


# ═══════════════════════════════════════════════════════════════
# GET /status/{job_id}
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


# ═══════════════════════════════════════════════════════════════
# POST /generate-clips/{job_id}
# ═══════════════════════════════════════════════════════════════
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
        raise HTTPException(400, f"Job ainda não concluído (status: {job['status']})")
    scenes = job.get("scenes")
    if not scenes:
        raise HTTPException(400, "Nenhuma cena encontrada neste job")
    if job.get("videos_status") == "processing":
        return {"message": "Geração de vídeos já em andamento", "job_id": job_id}
    jobs_db[job_id]["videos_status"] = "processing"
    jobs_db[job_id]["video_clips"]   = None
    background_tasks.add_task(process_video_clips, job_id=job_id, mode=mode)
    total_scenes = len([s for s in scenes if s.get("success", False)])
    return {
        "job_id":         job_id,
        "status":         "processing",
        "message":        f"Gerando {total_scenes} clipes de vídeo com Kling AI...",
        "estimated_cost": f"~${total_scenes * (0.14 if mode == 'std' else 0.28):.2f}",
        "mode":           mode,
    }


# ═══════════════════════════════════════════════════════════════
# POST /lipsync/{job_id}
# ✅ Aplica lip sync em TODOS os clipes individualmente
# ═══════════════════════════════════════════════════════════════
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
        raise HTTPException(400, "Áudio do job não encontrado")

    face_source = None

    if face_image:
        face_filename = f"{job_id}_lipsync_face_{face_image.filename}"
        face_path     = os.path.join(UPLOAD_DIR, face_filename)
        with open(face_path, "wb") as f:
            f.write(await face_image.read())
        face_source = face_path
        print(f"✅ Rosto recebido via upload: {face_filename}")

    elif face_url:
        face_source = face_url
        print(f"✅ Rosto recebido via URL: {face_url[:80]}")

    elif job.get("ref_image_path") and os.path.exists(job["ref_image_path"]):
        face_source = job["ref_image_path"]
        print(f"✅ Reutilizando ref_image do job: {os.path.basename(face_source)}")

    else:
        raise HTTPException(
            400,
            "Nenhuma imagem do personagem encontrada. "
            "Envie 'face_image' (arquivo), 'face_url' (URL pública) "
            "ou inclua uma ref_image ao criar o job com /generate."
        )

    if job.get("lipsync_status") == "processing":
        return {"message": "Lip sync já em andamento", "job_id": job_id}

    video_clips = job.get("video_clips", [])
    successful  = [c for c in video_clips if c.get("success") and c.get("video_url")]
    total_clips = len(successful)

    jobs_db[job_id]["lipsync_status"] = "processing"
    jobs_db[job_id]["lipsync_url"]    = None
    jobs_db[job_id]["lipsync_clips"]  = None

    background_tasks.add_task(
        process_lipsync,
        job_id=job_id,
        face_source=face_source,
        audio_path=audio_path,
        model=model,
    )

    return {
        "job_id":       job_id,
        "status":       "processing",
        "message":      f"Lip sync iniciado em {total_clips} clipe(s) individualmente",
        "total_clips":  total_clips,
        "face":         face_url if face_url else os.path.basename(face_source),
        "audio":        os.path.basename(audio_path),
        "model":        model,
    }


# ═══════════════════════════════════════════════════════════════
# POST /merge/{job_id}
# ✅ Usa lipsync_clips se disponível, senão video_clips
# ═══════════════════════════════════════════════════════════════
@router.post("/merge/{job_id}")
async def merge_final_video(job_id: str, background_tasks: BackgroundTasks):
    if job_id not in jobs_db:
        raise HTTPException(404, "Job not found")
    job = jobs_db[job_id]

    # Aceita merge se clipes normais OU lipsync estiverem prontos
    videos_ok  = job.get("videos_status") == "completed"
    lipsync_ok = job.get("lipsync_status") == "completed"

    if not videos_ok and not lipsync_ok:
        raise HTTPException(400, "Clipes ainda não gerados. Gere os clipes primeiro.")

    # ✅ Prioriza lipsync_clips; fallback para video_clips
    clips_to_use = job.get("lipsync_clips") or job.get("video_clips", [])
    successful   = [c for c in clips_to_use if c.get("success") and c.get("video_url")]

    if not successful:
        raise HTTPException(400, "Nenhum clipe disponível para merge")
    if job.get("merge_status") == "processing":
        return {"message": "Merge já em andamento", "job_id": job_id}

    jobs_db[job_id]["merge_status"] = "processing"
    jobs_db[job_id]["merge_url"]    = None
    background_tasks.add_task(process_merge, job_id)

    source = "lip sync" if lipsync_ok and job.get("lipsync_clips") else "clipes originais"
    return {
        "job_id":  job_id,
        "status":  "processing",
        "message": f"Iniciando merge de {len(successful)} clipes ({source}) + áudio...",
        "clips":   len(successful),
        "source":  source,
    }


# ═══════════════════════════════════════════════════════════════
# GET /download/{job_id}
# ═══════════════════════════════════════════════════════════════
@router.get("/download/{job_id}")
async def download_merged_video(job_id: str):
    if job_id not in jobs_db:
        raise HTTPException(404, "Job not found")
    job = jobs_db[job_id]
    if job.get("merge_status") != "completed":
        raise HTTPException(400, "Merge ainda não concluído")

    local_path = os.path.join(MERGE_OUTPUT_DIR, f"final_{job_id}.mp4")
    if not os.path.exists(local_path):
        raise HTTPException(404, "Arquivo de merge não encontrado")

    return FileResponse(
        path=local_path,
        media_type="video/mp4",
        filename=f"clipvox_{job_id}.mp4"
    )


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
        print(f"🎵 Analisando áudio: {job['audio_path']}")
        audio_metadata            = analyze_audio_cinematic(job["audio_path"], duration_override=virtual_duration)
        job["audio_duration"]     = audio_metadata["duration"]
        job["audio_bpm"]          = audio_metadata["bpm"]
        job["audio_key"]          = audio_metadata["key"]
        job["audio_energy_profile"] = audio_metadata["energy_profile"]
        update_job(job_id, progress=18)
        time.sleep(1)
        update_job(job_id, progress=22, current_step="calculating_scenes")
        print(f"🎬 Calculando cenas cinematográficas...")
        scene_structure        = calculate_cinematic_scenes(audio_metadata, job["description"])
        print(get_scene_summary(scene_structure))
        job["total_scenes"]    = scene_structure["total_scenes"]
        job["total_segments"]  = scene_structure["total_segments"]
        update_job(job_id, progress=28)
        update_job(job_id, progress=30, current_step="creative")
        print(f"🎨 Gerando conceito criativo com Claude API...")
        creative_concept = generate_creative_concept_with_prompts(
            audio_metadata, scene_structure, job["description"], job["style"]
        )
        job["creative_concept"] = creative_concept
        update_job(job_id, progress=58)
        time.sleep(2)
        update_job(job_id, progress=60, current_step="scenes")
        print(f"🎨 Gerando {len(creative_concept['scenes'])} imagens com Stability AI...")
        scenes_with_images = generate_scenes_batch(
            creative_concept["scenes"],
            style                = job["style"],
            aspect_ratio         = job["aspect_ratio"],
            resolution           = job["resolution"],
            reference_image_path = job.get("ref_image_path"),
            job_id               = job_id,
        )
        job["scenes"]        = scenes_with_images
        scenes_generated     = sum(1 for s in scenes_with_images if s.get("success", False))
        update_job(job_id, progress=min(60 + int((scenes_generated / len(scenes_with_images)) * 20), 80))
        print(f"✅ {scenes_generated}/{len(scenes_with_images)} imagens geradas")
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
        update_job(job_id, progress=98, current_step="final")
        print(f"✅ Pipeline concluído: {job_id}")
        update_job(job_id, status="completed", progress=100, current_step="done",
                   output_file=f"video_{job_id}.mp4", videos_status="ready")
    except Exception as e:
        print(f"❌ Erro no job {job_id}: {e}")
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
        print(f"\n🎬 Gerando {len(valid_scenes)} clipes de vídeo (Kling/{mode})")
        print(f"   Job: {job_id} | BPM: {bpm:.0f} | AR: {aspect_ratio}")
        video_results = generate_videos_batch(
            scenes=valid_scenes,
            bpm=bpm,
            aspect_ratio=aspect_ratio,
            mode=mode,
            job_id=job_id,
        )
        success_count = sum(1 for r in video_results if r.get("success", False))
        print(f"✅ Clipes gerados: {success_count}/{len(valid_scenes)}")
        jobs_db[job_id]["video_clips"]   = video_results
        jobs_db[job_id]["videos_status"] = "completed"
    except Exception as e:
        print(f"❌ Erro ao gerar clipes para job {job_id}: {e}")
        import traceback; traceback.print_exc()
        jobs_db[job_id]["videos_status"] = "failed"
        jobs_db[job_id]["videos_error"]  = str(e)


def process_lipsync(job_id: str, face_source: str, audio_path: str, model: str):
    """
    ✅ NOVO: Aplica lip sync em CADA clipe individualmente.
    Resultado salvo em lipsync_clips — merge usa esses clipes sincronizados.
    """
    print(f"\n🎤 Lip sync em todos os clipes — job {job_id} | model: {model}")
    job = jobs_db.get(job_id, {})

    video_clips      = job.get("video_clips") or []
    successful_clips = sorted(
        [c for c in video_clips if c.get("success") and c.get("video_url")],
        key=lambda x: x.get("scene_number", 0)
    )

    if not successful_clips:
        jobs_db[job_id]["lipsync_status"] = "failed"
        jobs_db[job_id]["lipsync_error"]  = "Nenhum video_clip disponível."
        print(f"❌ Lip sync falhou: sem video_clips disponíveis")
        return

    total          = len(successful_clips)
    lipsync_clips  = []
    success_count  = 0

    for i, clip in enumerate(successful_clips):
        scene_num      = clip.get("scene_number", i + 1)
        face_video_url = clip.get("kling_url") or clip.get("video_url")

        print(f"\n🎤 Lip sync clipe {i+1}/{total} (cena {scene_num})...")
        print(f"   🎬 Vídeo: {face_video_url[:80]}")

        # Lip sync individual — job_id único por clipe para não sobrescrever R2
        clip_job_id = f"{job_id}_scene{scene_num:03d}"

        result = generate_lipsync(
            face_source=face_video_url,
            audio_source=audio_path,
            job_id=clip_job_id,
            model=model,
        )

        if result["success"]:
            success_count += 1
            lipsync_clips.append({
                "success":      True,
                "scene_number": scene_num,
                "video_url":    result["video_url"],  # URL do clipe com lip sync
                "original_url": face_video_url,
            })
            print(f"   ✅ Clipe {scene_num} sincronizado: {result['video_url'][:80]}")
        else:
            # Fallback: usa clipe original se lip sync falhar
            print(f"   ⚠️ Lip sync falhou na cena {scene_num} — usando clipe original")
            lipsync_clips.append({
                "success":      True,  # marcado como success para não bloquear merge
                "scene_number": scene_num,
                "video_url":    clip.get("video_url"),
                "original_url": face_video_url,
                "lipsync_error": result.get("error"),
            })

    jobs_db[job_id]["lipsync_clips"]  = lipsync_clips
    jobs_db[job_id]["lipsync_status"] = "completed"

    # lipsync_url aponta para o primeiro clipe sincronizado (preview)
    first_ok = next((c for c in lipsync_clips if c.get("success")), None)
    if first_ok:
        jobs_db[job_id]["lipsync_url"] = first_ok["video_url"]

    print(f"\n✅ Lip sync concluído: {success_count}/{total} clipes sincronizados")


def process_merge(job_id: str):
    """
    ✅ Usa lipsync_clips se disponível, senão video_clips originais.
    """
    job = jobs_db.get(job_id)
    if not job:
        return
    try:
        # Prioridade: clipes com lip sync → clipes originais
        lipsync_clips = job.get("lipsync_clips")
        video_clips   = job.get("video_clips", [])

        if lipsync_clips:
            clips_source = "lip sync"
            clips        = lipsync_clips
        else:
            clips_source = "originais"
            clips        = video_clips

        successful = sorted(
            [c for c in clips if c.get("success") and c.get("video_url")],
            key=lambda x: x.get("scene_number", 0)
        )
        video_urls = [c["video_url"] for c in successful]
        audio_path = job.get("audio_path")

        print(f"\n🎬 Merge: {len(video_urls)} clipes ({clips_source}) + áudio")

        result = merge_clips_with_audio(
            video_urls=video_urls,
            audio_path=audio_path,
            job_id=job_id,
        )

        if result["success"]:
            jobs_db[job_id]["merge_status"] = "completed"
            if result.get("output_url"):
                jobs_db[job_id]["merge_url"] = result["output_url"]
                print(f"✅ Merge concluído (R2): {result['output_url']}")
            else:
                backend_url  = os.getenv("BACKEND_URL", "https://clipvox-backend.onrender.com")
                download_url = f"{backend_url}/api/videos/download/{job_id}"
                jobs_db[job_id]["merge_url"] = download_url
                print(f"✅ Merge concluído (download local): {download_url}")
        else:
            jobs_db[job_id]["merge_status"] = "failed"
            jobs_db[job_id]["merge_error"]  = result.get("error")
            print(f"❌ Merge falhou: {result.get('error')}")

    except Exception as e:
        import traceback; traceback.print_exc()
        jobs_db[job_id]["merge_status"] = "failed"
        jobs_db[job_id]["merge_error"]  = str(e)


def update_job(job_id: str, **kwargs):
    if job_id in jobs_db:
        jobs_db[job_id].update(kwargs)
