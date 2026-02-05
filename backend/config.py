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

# 🆕 FEATURE 4: ESTILOS EXPANDIDOS (10+ estilos)
# ────────────────────────────────────────────────────────────────
VISUAL_STYLES = {
    "realistic": {
        "prefix": "photorealistic, cinematic photography, 8K HDR, professional camera, film grain, natural lighting, high detail",
        "label": "Fotorrealista"
    },
    "cinematic": {
        "prefix": "cinematic masterpiece, anamorphic lens, epic composition, dramatic lighting, color grading, film still, Blade Runner aesthetic",
        "label": "Cinemático"
    },
    "animated": {
        "prefix": "3D animation style, Pixar quality, vibrant colors, expressive, detailed render, studio ghibli influence",
        "label": "Animado 3D"
    },
    "retro": {
        "prefix": "retro 1980s aesthetic, VHS style, synthwave colors, vintage film grain, neon lights, nostalgic",
        "label": "Retro 80s"
    },
    "anime": {
        "prefix": "anime style, Studio Ghibli aesthetic, vibrant colors, hand-drawn animation, Japanese animation, detailed character design, expressive faces",
        "label": "Anime"
    },
    "cyberpunk": {
        "prefix": "cyberpunk aesthetic, neon lights, futuristic cityscape, Blade Runner 2049 style, rain-soaked streets, holographic displays, dystopian atmosphere, high-tech low-life",
        "label": "Cyberpunk"
    },
    "fantasy": {
        "prefix": "fantasy art, magical atmosphere, ethereal lighting, concept art style, epic fantasy composition, mystical elements, enchanted forest, mythical creatures",
        "label": "Fantasia"
    },
    "minimalist": {
        "prefix": "minimalist design, clean composition, negative space, geometric shapes, modern aesthetic, simple color palette, elegant simplicity",
        "label": "Minimalista"
    },
    "vintage": {
        "prefix": "vintage film photography, classic cinema aesthetic, warm sepia tones, film scratches, old Hollywood glamour, timeless elegance, nostalgic atmosphere",
        "label": "Vintage"
    },
    "oil_painting": {
        "prefix": "oil painting style, renaissance art, brushstroke texture, classical art technique, rich colors, fine art painting, museum quality, detailed brushwork",
        "label": "Pintura a Óleo"
    }
}

# 🆕 FEATURE 2: ASPECT RATIOS SUPORTADOS
# ────────────────────────────────────────────────────────────────
ASPECT_RATIOS = {
    "16:9": {"label": "Horizontal", "desc": "1920×1080"},
    "9:16": {"label": "Vertical (Stories)", "desc": "1080×1920"},
    "1:1": {"label": "Quadrado (Instagram)", "desc": "1080×1080"},
    "4:3": {"label": "Clássico", "desc": "1440×1080"}
}

# 🆕 FEATURE 3: RESOLUÇÕES SUPORTADAS
# ────────────────────────────────────────────────────────────────
RESOLUTIONS = {
    "720p": {
        "label": "HD 720p",
        "desc": "Rápido e econômico",
        "cost_multiplier": 1.0  # Base cost
    },
    "1080p": {
        "label": "Full HD 1080p",
        "desc": "Qualidade premium",
        "cost_multiplier": 1.54  # ~54% mais caro
    }
}
