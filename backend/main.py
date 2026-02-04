from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
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
    allow_origins=["*"],  # Em produção, especificar domínios
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
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
    return {"error": "File not found"}, 404

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
