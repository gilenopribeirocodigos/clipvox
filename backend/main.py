from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
import os

from config import UPLOAD_DIR
from database import init_db
from routes import videos

os.makedirs(UPLOAD_DIR, exist_ok=True)

app = FastAPI(
    title="ClipVox API",
    description="AI-powered music video generator",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    return JSONResponse(
        status_code=500,
        content={"detail": str(exc), "error": "Internal server error"},
        headers={
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Methods": "*",
            "Access-Control-Allow-Headers": "*",
        },
    )


app.include_router(videos.router, prefix="/api/videos", tags=["videos"])


@app.api_route("/", methods=["GET", "HEAD"])
async def root():
    return {
        "status": "ok",
        "service": "clipvox-backend",
        "message": "ClipVox backend is running",
    }


@app.api_route("/health", methods=["GET", "HEAD"])
async def health_root():
    return {"status": "ok"}


@app.api_route("/api/health", methods=["GET", "HEAD"])
async def health_api():
    return {"status": "ok", "message": "ClipVox API running"}


@app.get("/api/files/{filename}")
async def serve_file(filename: str):
    file_path = os.path.join(UPLOAD_DIR, filename)
    if os.path.exists(file_path):
        return FileResponse(file_path)
    return JSONResponse(status_code=404, content={"error": "File not found"})


@app.on_event("startup")
async def startup_event():
    init_db()
    print("🚀 ClipVox Backend started!")
    print(f"📁 Upload directory: {UPLOAD_DIR}")
    print("🎬 Ready to generate videos!")


if __name__ == "__main__":
    import uvicorn

    port = int(os.getenv("PORT", 8000))
    uvicorn.run("main:app", host="0.0.0.0", port=port, reload=False)
