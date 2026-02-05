import os

# ─── Database ─────────────────────────────────────────────────
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./clipvox.db")

# ─── Security ─────────────────────────────────────────────────
SECRET_KEY = os.getenv("SECRET_KEY", "clipvox-dev-secret-change-in-production")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24 * 7  # 7 days

# ─── API Keys ─────────────────────────────────────────────────
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")
STABILITY_API_KEY = os.getenv("STABILITY_API_KEY", "")

# ─── CloudFlare R2 Storage ────────────────────────────────────
R2_ACCESS_KEY_ID = os.getenv("R2_ACCESS_KEY_ID", "")
R2_SECRET_ACCESS_KEY = os.getenv("R2_SECRET_ACCESS_KEY", "")
R2_ENDPOINT_URL = os.getenv("R2_ENDPOINT_URL", "")
R2_BUCKET_NAME = os.getenv("R2_BUCKET_NAME", "clipvox-scenes")
R2_PUBLIC_URL = os.getenv("R2_PUBLIC_URL", "")  # https://pub-xxxxx.r2.dev

# ─── Local Storage (Temporário) ───────────────────────────────
UPLOAD_DIR = os.getenv("UPLOAD_DIR", "/tmp/clipvox_uploads")
os.makedirs(UPLOAD_DIR, exist_ok=True)

# ─── Credits System ───────────────────────────────────────────
FREE_CREDITS_ON_SIGNUP = 500
CREDITS_PER_VIDEO = 100

# ─── Cinematic Scene Calculation ─────────────────────────────
SCENE_DURATION_LOW_ENERGY = 6.5
SCENE_DURATION_MID_ENERGY = 4.0
SCENE_DURATION_HIGH_ENERGY = 2.5

MIN_SCENES = 20
MAX_SCENES = 120

CINEMATIC_DENSITY_FACTOR = 1.6

CAMERA_MOVEMENTS = [
    "static shot",
    "slow pan left to right",
    "slow pan right to left", 
    "dolly in",
    "dolly out",
    "crane up",
    "crane down",
    "tracking shot",
    "handheld",
    "aerial view",
    "low angle",
    "high angle",
    "dutch angle",
    "zoom in",
    "zoom out"
]

TRANSITIONS = ["cut", "dissolve", "fade", "wipe"]
