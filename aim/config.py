"""Settings loader for Aim.

อ่านค่าจาก env ก่อน แล้ว fallback ไปไฟล์ secrets (AIM_SECRETS_FILE).
ตั้งใจให้ไม่มี dependency ภายนอก เพื่อให้รันใน container เปล่าได้.
"""
from __future__ import annotations

import os
from pathlib import Path

DEFAULT_QDRANT_URL = "http://qdrant:6333"  # ใน docker network 'backend'
DEFAULT_COLLECTION = "capability_catalog"
DEFAULT_MODEL = "anthropic/claude-sonnet-4"
DEFAULT_OPENROUTER_BASE = "https://openrouter.ai/api/v1"


def _load_env_file(path: str | None) -> dict[str, str]:
    out: dict[str, str] = {}
    if not path:
        return out
    p = Path(path)
    if not p.exists():
        return out
    for line in p.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        out[k.strip()] = v.strip().strip('"').strip("'")
    return out


def load_settings() -> dict:
    secrets = _load_env_file(os.environ.get("AIM_SECRETS_FILE"))

    def get(key: str, default: str | None = None) -> str | None:
        return os.environ.get(key) or secrets.get(key) or default

    return {
        "qdrant_url": get("QDRANT_URL", DEFAULT_QDRANT_URL),
        "collection": get("AIM_COLLECTION", DEFAULT_COLLECTION),
        "openrouter_key": get("OPENROUTER_API_KEY"),
        "openrouter_base": get("OPENROUTER_BASE_URL", DEFAULT_OPENROUTER_BASE),
        "model": get("OPENROUTER_DEFAULT_MODEL", DEFAULT_MODEL),
    }
