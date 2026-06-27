"""M2 indexer — embed capability catalog เข้า Qdrant collection.

ใช้ FastEmbed (all-MiniLM-L6-v2, 384d) ให้ตรง space กับ qdrant-mcp เดิม.
Qdrant REST ผ่าน urllib (stdlib). idempotent: upsert ด้วย stable uuid id.
"""
from __future__ import annotations

import json
import urllib.error
import urllib.request
import uuid
from pathlib import Path

VECTOR_SIZE = 384
# multilingual (รองรับไทย) — all-MiniLM-L6-v2 อ่อนภาษาไทย recall แย่
MODEL_NAME = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
DATA_PATH = Path(__file__).resolve().parent.parent / "data" / "catalog.json"


def _req(url: str, payload: dict | None = None, method: str = "GET") -> dict:
    data = json.dumps(payload).encode() if payload is not None else None
    req = urllib.request.Request(
        url, data=data, method=method,
        headers={"Content-Type": "application/json"} if data else {},
    )
    with urllib.request.urlopen(req, timeout=120) as resp:
        return json.loads(resp.read().decode())


def _embed_text(cap: dict) -> str:
    return (
        f"{cap.get('name','')} — {cap.get('when_to_use','')} "
        f"{cap.get('summary_th','')} [{cap.get('subcategory','')}] "
        f"({cap.get('domain','')})"
    )


def _ensure_collection(base: str, coll: str) -> None:
    cfg = {"vectors": {"size": VECTOR_SIZE, "distance": "Cosine"}}
    try:
        _req(f"{base}/collections/{coll}", cfg, method="PUT")
        print(f"[aim] created collection '{coll}'")
    except urllib.error.HTTPError as exc:
        if exc.code in (400, 409):
            print(f"[aim] collection '{coll}' มีอยู่แล้ว — upsert ทับ")
        else:
            raise


def cmd_index(settings: dict) -> int:
    from fastembed import TextEmbedding

    base = settings["qdrant_url"].rstrip("/")
    coll = settings["collection"]

    catalog = json.loads(DATA_PATH.read_text(encoding="utf-8"))
    caps = catalog.get("capabilities", [])
    if not caps:
        print(f"[aim] no capabilities in {DATA_PATH}")
        return 1

    texts = [_embed_text(c) for c in caps]
    print(f"[aim] embedding {len(texts)} capabilities ({MODEL_NAME}) ...")
    model = TextEmbedding(model_name=MODEL_NAME)
    vectors = [v.tolist() for v in model.embed(texts)]

    _ensure_collection(base, coll)

    points = []
    for cap, vec in zip(caps, vectors):
        pid = str(uuid.uuid5(uuid.NAMESPACE_URL, f"{cap.get('source')}/{cap.get('name')}"))
        points.append({"id": pid, "vector": vec, "payload": cap})

    _req(f"{base}/collections/{coll}/points?wait=true", {"points": points}, method="PUT")
    info = _req(f"{base}/collections/{coll}")
    count = info.get("result", {}).get("points_count")
    print(f"[aim] indexed -> '{coll}' points_count={count}")
    return 0
