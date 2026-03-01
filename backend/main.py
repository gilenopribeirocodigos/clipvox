from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse
import os
from config import UPLOAD_DIR
from database import init_db

# Create upload directory
os.makedirs(UPLOAD_DIR, exist_ok=True)

# Initialize FastAPI app
app = FastAPI(
    title="ClipVox API",
    description="AI-powered music video generator",
    version="1.0.0"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ✅ CORREÇÃO 3: Exception handler global que inclui headers CORS
# Sem isso, erros 500/504 retornam sem Access-Control-Allow-Origin
# e o browser reporta CORS em vez do erro real
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    return JSONResponse(
        status_code=500,
        content={"detail": str(exc), "error": "Internal server error"},
        headers={
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Methods": "*",
            "Access-Control-Allow-Headers": "*",
        }
    )

# Import routes
from routes import videos

# Register routes
app.include_router(videos.router, prefix="/api/videos", tags=["videos"])

# Health check
@app.get("/api/health")
async def health():
    return {"status": "ok", "message": "ClipVox API running"}

# Serve uploaded files
@app.get("/api/files/{filename}")
async def serve_file(filename: str):
    file_path = os.path.join(UPLOAD_DIR, filename)
    if os.path.exists(file_path):
        return FileResponse(file_path)
    return JSONResponse(status_code=404, content={"error": "File not found"})

# Initialize database on startup
@app.on_event("startup")
async def startup_event():
    init_db()
    print("🚀 ClipVox Backend started!")
    print(f"📁 Upload directory: {UPLOAD_DIR}")
    print(f"🎬 Ready to generate videos!")

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
