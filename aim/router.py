"""M3 router — รับงานเป็นข้อความ -> semantic search -> top-N capability ที่ใช่.

embed query ด้วยโมเดลเดียวกับตอน index (all-MiniLM-L6-v2, 384d) แล้วค้นใน Qdrant.
"""
from __future__ import annotations

from .index import MODEL_NAME, _req

_TIER_ICON = {"must-have": "🟢", "nice-to-have": "🟡", "niche": "⚪"}
_TYPE_ICON = {"skill": "📄 skill", "mcp-tool": "🛠️ tool", "agent": "🤖 agent", "rag": "📚 rag"}


def cmd_route(settings: dict, task: str, top_k: int = 5,
              harness: str | None = None, use_llm: bool = False) -> int:
    from fastembed import TextEmbedding

    base = settings["qdrant_url"].rstrip("/")
    coll = settings["collection"]

    model = TextEmbedding(model_name=MODEL_NAME)
    qvec = list(model.embed([task]))[0].tolist()

    # ดึง candidate เผื่อไว้เยอะขึ้นถ้าจะ LLM re-rank
    limit = max(top_k * 2, 12) if use_llm else top_k
    body: dict = {"vector": qvec, "limit": limit, "with_payload": True}
    if harness:
        body["filter"] = {"should": [
            {"key": "harness", "match": {"value": harness}},
            {"key": "harness", "match": {"value": "both"}},
        ]}

    res = _req(f"{base}/collections/{coll}/points/search", body, method="POST")
    hits = res.get("result", [])

    print(f"\n🎯 งาน: {task}")

    picks = None
    if use_llm:
        from .llm import rerank
        picks = rerank(settings, task, hits, top_k)

    if picks:
        by_name = {h.get("payload", {}).get("name"): h.get("payload", {}) for h in hits}
        print(f"   แนะนำ {len(picks)} capability (LLM re-ranked):\n")
        for i, pick in enumerate(picks, 1):
            p = by_name.get(pick.get("name"), {})
            icon = _TIER_ICON.get(p.get("tier"), "")
            tlabel = _TYPE_ICON.get(p.get("type", "skill"), "")
            print(f"{i}. {icon} {pick.get('name')}  [{tlabel}]  ({p.get('domain')}/{p.get('subcategory')})")
            print(f"   เหตุผล: {pick.get('why')}")
            if p.get("url"):
                print(f"   {p.get('url')}")
            print()
        return 0

    hits = hits[:top_k]
    print(f"   แนะนำ {len(hits)} capability ที่ใช่ที่สุด:\n")
    for i, h in enumerate(hits, 1):
        p = h.get("payload", {})
        icon = _TIER_ICON.get(p.get("tier"), "")
        tlabel = _TYPE_ICON.get(p.get("type", "skill"), "")
        print(f"{i}. {icon} {p.get('name')}  [{tlabel}]  ({p.get('domain')}/{p.get('subcategory')})  ~{h.get('score'):.3f}")
        print(f"   {p.get('summary_th')}")
        print(f"   {p.get('url')}\n")
    return 0
