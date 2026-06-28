"""Local backend — ค้น capability ในเครื่อง (brute-force cosine) ไม่ต้องใช้ Qdrant/server.

192 capabilities เล็กพอที่จะ embed + ค้นในหน่วยความจำได้เร็วมาก.
local index เก็บที่ data/local_index.json (vectors), payload ดึงจาก catalog.json.
"""
from __future__ import annotations

import json
import math
from pathlib import Path

from .index import DATA_PATH, MODEL_NAME, _embed_text

LOCAL_INDEX = DATA_PATH.parent / "local_index.json"


def _load_caps() -> list[dict]:
    return json.loads(DATA_PATH.read_text(encoding="utf-8")).get("capabilities", [])


def build_local_index(settings: dict) -> int:
    """embed ทุก capability ในเครื่อง แล้วเซฟ vectors ลง local_index.json."""
    from fastembed import TextEmbedding

    caps = _load_caps()
    if not caps:
        print(f"[aim] no capabilities in {DATA_PATH}")
        return 1
    texts = [_embed_text(c) for c in caps]
    print(f"[aim] (local) embedding {len(texts)} capabilities ({MODEL_NAME}) ...")
    model = TextEmbedding(model_name=MODEL_NAME)
    vecs = [v.tolist() for v in model.embed(texts)]
    items = [
        {"name": c.get("name"), "source": c.get("source"), "vector": v}
        for c, v in zip(caps, vecs)
    ]
    LOCAL_INDEX.write_text(
        json.dumps({"model": MODEL_NAME, "count": len(items), "items": items}, ensure_ascii=False),
        encoding="utf-8",
    )
    print(f"[aim] (local) indexed -> {LOCAL_INDEX.name} ({len(items)} vectors)")
    return 0


def _cosine(a: list[float], b: list[float]) -> float:
    dot = sum(x * y for x, y in zip(a, b))
    na = math.sqrt(sum(x * x for x in a))
    nb = math.sqrt(sum(y * y for y in b))
    return dot / (na * nb) if na and nb else 0.0


def local_search(task: str, top_k: int, settings: dict, harness: str | None = None) -> list[dict]:
    from fastembed import TextEmbedding

    if not LOCAL_INDEX.exists():
        raise FileNotFoundError(
            f"{LOCAL_INDEX} ยังไม่มี — รัน `python -m aim index --local` ก่อน"
        )
    idx = json.loads(LOCAL_INDEX.read_text(encoding="utf-8"))
    by_key = {(c.get("source"), c.get("name")): c for c in _load_caps()}

    model = TextEmbedding(model_name=MODEL_NAME)
    qvec = list(model.embed([task]))[0].tolist()

    scored: list[dict] = []
    for it in idx.get("items", []):
        payload = by_key.get((it.get("source"), it.get("name")))
        if payload is None:
            continue
        if harness and payload.get("harness") not in (harness, "both"):
            continue
        scored.append({"score": _cosine(qvec, it["vector"]), "payload": payload})
    scored.sort(key=lambda x: x["score"], reverse=True)
    return scored[:top_k]
