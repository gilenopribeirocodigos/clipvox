"""
📦 ClipVox — Persistência de Jobs no Supabase
Mantém jobs_db em memória (rápido) + sincroniza com Supabase (sobrevive a restarts).

SQL para criar a tabela (rode no Supabase SQL Editor):
  CREATE TABLE IF NOT EXISTS clipvox_jobs (
    id         TEXT PRIMARY KEY,
    data       JSONB NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
  );
  CREATE INDEX IF NOT EXISTS idx_clipvox_jobs_created ON clipvox_jobs(created_at DESC);
"""

import os
import json
import time

SUPABASE_URL = os.getenv("SUPABASE_URL", "")
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_KEY") or os.getenv("SUPABASE_KEY", "")

_client = None


def _get_client():
    global _client
    if _client:
        return _client
    if not SUPABASE_URL or not SUPABASE_KEY:
        print("⚠️ Supabase não configurado — jobs apenas em memória")
        return None
    try:
        from supabase import create_client
        _client = create_client(SUPABASE_URL, SUPABASE_KEY)
        print("✅ Supabase conectado (job persistence ativo)")
        return _client
    except Exception as e:
        print(f"⚠️ Supabase init error: {e}")
        return None


# ── Campos que NÃO precisam ir pro Supabase (grandes, só em memória) ──────────
# scenes contém prompts longos — mantemos mas truncamos a 50 cenas
_SKIP_FIELDS: set = set()  # nada pulado — armazenamos tudo


def _safe_serialize(data: dict) -> str:
    """Serializa job para JSON, tratando tipos não-serializáveis."""
    def default(obj):
        if isinstance(obj, (int, float, str, bool, type(None))):
            return obj
        return str(obj)
    return json.dumps(data, default=default)


# ═══════════════════════════════════════════════════════════════
# SAVE / LOAD
# ═══════════════════════════════════════════════════════════════

def save_job(job_id: str, data: dict) -> bool:
    """Persiste job no Supabase (upsert). Retorna True se ok."""
    client = _get_client()
    if not client:
        return False
    try:
        payload = {
            "id":         job_id,
            "data":       json.loads(_safe_serialize(data)),
            "updated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        }
        client.table("clipvox_jobs").upsert(payload).execute()
        return True
    except Exception as e:
        print(f"⚠️ Supabase save_job error: {e}")
        return False


def load_job(job_id: str) -> dict | None:
    """Carrega job do Supabase. Retorna None se não encontrado."""
    client = _get_client()
    if not client:
        return None
    try:
        result = (
            client.table("clipvox_jobs")
            .select("data")
            .eq("id", job_id)
            .limit(1)
            .execute()
        )
        rows = result.data or []
        if rows:
            return rows[0]["data"]
        return None
    except Exception as e:
        print(f"⚠️ Supabase load_job error: {e}")
        return None


def load_recent_jobs(limit: int = 100) -> dict:
    """
    Carrega jobs recentes do Supabase para popular jobs_db em memória.
    Chamado no startup do servidor.
    """
    client = _get_client()
    if not client:
        return {}
    try:
        result = (
            client.table("clipvox_jobs")
            .select("id, data")
            .order("created_at", desc=True)
            .limit(limit)
            .execute()
        )
        jobs = {}
        for row in result.data or []:
            try:
                jobs[row["id"]] = row["data"]
            except Exception:
                pass
        print(f"✅ Supabase: {len(jobs)} jobs carregados do histórico")
        return jobs
    except Exception as e:
        print(f"⚠️ Supabase load_recent_jobs error: {e}")
        return {}
