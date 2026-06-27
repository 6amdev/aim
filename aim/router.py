"""M3 router — รับงานเป็นข้อความ -> semantic search -> top-N capability ที่ใช่.

embed query ด้วยโมเดลเดียวกับตอน index (all-MiniLM-L6-v2, 384d) แล้วค้นใน Qdrant.
"""
from __future__ import annotations

from .index import MODEL_NAME, _req

_TIER_ICON = {"must-have": "🟢", "nice-to-have": "🟡", "niche": "⚪"}


def cmd_route(settings: dict, task: str, top_k: int = 5, harness: str | None = None) -> int:
    from fastembed import TextEmbedding

    base = settings["qdrant_url"].rstrip("/")
    coll = settings["collection"]

    model = TextEmbedding(model_name=MODEL_NAME)
    qvec = list(model.embed([task]))[0].tolist()

    body: dict = {"vector": qvec, "limit": top_k, "with_payload": True}
    if harness:
        body["filter"] = {"should": [
            {"key": "harness", "match": {"value": harness}},
            {"key": "harness", "match": {"value": "both"}},
        ]}

    res = _req(f"{base}/collections/{coll}/points/search", body, method="POST")
    hits = res.get("result", [])

    print(f"\n🎯 งาน: {task}")
    print(f"   แนะนำ {len(hits)} capability ที่ใช่ที่สุด:\n")
    for i, h in enumerate(hits, 1):
        p = h.get("payload", {})
        icon = _TIER_ICON.get(p.get("tier"), "")
        print(f"{i}. {icon} {p.get('name')}  ({p.get('domain')}/{p.get('subcategory')})  ~{h.get('score'):.3f}")
        print(f"   {p.get('summary_th')}")
        print(f"   {p.get('url')}\n")
    return 0
