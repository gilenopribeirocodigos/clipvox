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

# ─── Storage ──────────────────────────────────────────────────
UPLOAD_DIR = os.getenv("UPLOAD_DIR", "/tmp/clipvox_uploads")
os.makedirs(UPLOAD_DIR, exist_ok=True)

# ─── Credits System ───────────────────────────────────────────
FREE_CREDITS_ON_SIGNUP = 500
CREDITS_PER_VIDEO = 100

# ─── Cinematic Scene Calculation ─────────────────────────────
# Esses valores determinam a qualidade cinematográfica

# Duração de scenes baseada em energia
SCENE_DURATION_LOW_ENERGY = 6.5   # segundos - cenas longas e contemplativas
SCENE_DURATION_MID_ENERGY = 4.0   # segundos - ritmo médio
SCENE_DURATION_HIGH_ENERGY = 2.5  # segundos - cortes rápidos e dinâmicos

# Limites de scenes por vídeo
MIN_SCENES = 20   # vídeos muito curtos
MAX_SCENES = 120  # limite técnico e de custo

# Fator de densidade de cortes (quanto maior, mais scenes)
CINEMATIC_DENSITY_FACTOR = 1.6  # 1.0 = padrão, 2.0 = dobro de scenes

# Camera movements pool (variedade cinematográfica)
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

# Transition types
TRANSITIONS = ["cut", "dissolve", "fade", "wipe"]
