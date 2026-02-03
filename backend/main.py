from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from datetime import datetime
import uuid
import os

# ─── APP SETUP ────────────────────────────────────────────────
app = FastAPI(
    title="ClipVox API",
    description="API do gerador de videoclipes com IA",
    version="0.1.0"
)

# CORS - permite frontend conectar
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Em produção: coloca a URL do seu frontend
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ─── MODELOS (Pydantic) ───────────────────────────────────────
class HealthResponse(BaseModel):
    status: str
    timestamp: str
    version: str

class JobCreateRequest(BaseModel):
    description: str
    style: str = "realistic"  # realistic, cinematic, animated, retro

class JobResponse(BaseModel):
    job_id: str
    status: str
    created_at: str
    estimated_time: str

class JobStatusResponse(BaseModel):
    job_id: str
    status: str  # pending | analyzing | creative | scenes | segments | merging | completed | failed
    progress: int  # 0-100
    current_step: str
    created_at: str
    updated_at: str
    result_url: str | None = None

class CreditsResponse(BaseModel):
    total: int
    used: int
    available: int

# ─── SIMULAÇÃO DE DADOS (MVP sem banco) ─────────────────────
# Em breve vai usar PostgreSQL no Render
jobs_db: dict[str, dict] = {}
user_credits = {"total": 500, "used": 0}

STEPS_ORDER = [
    ("analyzing", "Input Analyzing", 15),
    ("creative", "Creative Concept", 30),
    ("scenes", "Scenes", 55),
    ("segments", "Video Segments", 80),
    ("merging", "Merge Final", 95),
    ("completed", "Completed", 100),
]

# ─── ROUTES ───────────────────────────────────────────────────

# Health check — Render usa isso para saber se o serviço tá vivo
@app.get("/health", response_model=HealthResponse)
async def health():
    return {
        "status": "ok",
        "timestamp": datetime.utcnow().isoformat(),
        "version": "0.1.0"
    }

# Creditos do usuário
@app.get("/api/credits", response_model=CreditsResponse)
async def get_credits():
    return {
        "total": user_credits["total"],
        "used": user_credits["used"],
        "available": user_credits["total"] - user_credits["used"]
    }

# Upload de áudio + criar job
@app.post("/api/jobs", response_model=JobResponse)
async def create_job(
    audio: UploadFile = File(...),
    description: str = "Videoclipe profissional",
    style: str = "realistic"
):
    # Validação do arquivo
    allowed_extensions = [".mp3", ".wav", ".ogg", ".m4a"]
    filename = audio.filename or ""
    ext = os.path.splitext(filename)[1].lower()

    if ext not in allowed_extensions:
        raise HTTPException(status_code=400, detail=f"Formato não suportado. Use: {', '.join(allowed_extensions)}")

    # Verifica créditos
    if user_credits["used"] >= user_credits["total"]:
        raise HTTPException(status_code=402, detail="Créditos insuficientes")

    # Cria job
    job_id = str(uuid.uuid4())[:12]
    now = datetime.utcnow().isoformat()

    jobs_db[job_id] = {
        "job_id": job_id,
        "status": "pending",
        "progress": 0,
        "current_step": "Aguardando processamento",
        "description": description,
        "style": style,
        "filename": filename,
        "created_at": now,
        "updated_at": now,
        "result_url": None
    }

    user_credits["used"] += 100  # 100 créditos por vídeo

    return {
        "job_id": job_id,
        "status": "pending",
        "created_at": now,
        "estimated_time": "3-5 minutos"
    }

# Status do job
@app.get("/api/jobs/{job_id}", response_model=JobStatusResponse)
async def get_job_status(job_id: str):
    if job_id not in jobs_db:
        raise HTTPException(status_code=404, detail="Job não encontrado")

    job = jobs_db[job_id]
    return job

# Lista todos os jobs
@app.get("/api/jobs")
async def list_jobs():
    return {"jobs": list(jobs_db.values())}

# Simula avanço do job (para testes no MVP)
@app.post("/api/jobs/{job_id}/advance")
async def advance_job(job_id: str):
    if job_id not in jobs_db:
        raise HTTPException(status_code=404, detail="Job não encontrado")

    job = jobs_db[job_id]
    current_status = job["status"]

    # Encontra o próximo passo
    status_list = ["pending"] + [s[0] for s in STEPS_ORDER]
    if current_status in status_list:
        idx = status_list.index(current_status)
        if idx < len(status_list) - 1:
            next_status = status_list[idx + 1]
            # Atualiza com dados do próximo passo
            for step_status, step_name, step_progress in STEPS_ORDER:
                if step_status == next_status:
                    job["status"] = step_status
                    job["current_step"] = step_name
                    job["progress"] = step_progress
                    job["updated_at"] = datetime.utcnow().isoformat()
                    break

            if next_status == "completed":
                job["result_url"] = f"/videos/{job_id}_final.mp4"

    return {"job_id": job_id, "status": job["status"], "progress": job["progress"]}

# ─── ENTRY POINT ──────────────────────────────────────────────
if __name__ == "__main__":
    import uvicorn
    # Porta: usa variável de ambiente PORT (Render define isso automaticamente)
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
