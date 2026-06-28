"""M3 router — รับงานเป็นข้อความ -> semantic search -> top-N capability ที่ใช่.

embed query ด้วยโมเดลเดียวกับตอน index (all-MiniLM-L6-v2, 384d) แล้วค้นใน Qdrant.
"""
from __future__ import annotations

from .index import MODEL_NAME, _req

_TIER_ICON = {"must-have": "🟢", "nice-to-have": "🟡", "niche": "⚪"}
_TYPE_ICON = {"skill": "📄 skill", "mcp-tool": "🛠️ tool", "agent": "🤖 agent", "rag": "📚 rag"}


def cmd_route(settings: dict, task: str, top_k: int = 5,
              harness: str | None = None, use_llm: bool = False,
              use_verify: bool = False, backend: str = "qdrant") -> int:
    if use_verify:
        use_llm = True  # verify ต้องมี picks จาก re-rank ก่อน

    # ดึง candidate เผื่อไว้เยอะขึ้นถ้าจะ LLM re-rank
    limit = max(top_k * 2, 12) if use_llm else top_k

    if backend == "local":
        from .local_store import local_search
        hits = local_search(task, limit, settings, harness)
    else:
        from fastembed import TextEmbedding
        base = settings["qdrant_url"].rstrip("/")
        coll = settings["collection"]
        qvec = list(TextEmbedding(model_name=MODEL_NAME).embed([task]))[0].tolist()
        body: dict = {"vector": qvec, "limit": limit, "with_payload": True}
        if harness:
            body["filter"] = {"should": [
                {"key": "harness", "match": {"value": harness}},
                {"key": "harness", "match": {"value": "both"}},
            ]}
        hits = _req(f"{base}/collections/{coll}/points/search", body, method="POST").get("result", [])

    print(f"\n🎯 งาน: {task}  [{backend}]")

    picks = None
    if use_llm:
        from .llm import rerank
        picks = rerank(settings, task, hits, top_k)

    if picks:
        by_name = {h.get("payload", {}).get("name"): h.get("payload", {}) for h in hits}

        verdict = None
        if use_verify:
            from .llm import verify
            verdict = verify(settings, task, picks, by_name)
            if verdict and verdict.get("verified"):
                keep = set(verdict["verified"])
                picks = [p for p in picks if p.get("name") in keep] or picks

        label = "LLM re-ranked + verified" if verdict else "LLM re-ranked"
        print(f"   แนะนำ {len(picks)} capability ({label}):\n")
        for i, pick in enumerate(picks, 1):
            p = by_name.get(pick.get("name"), {})
            icon = _TIER_ICON.get(p.get("tier"), "")
            tlabel = _TYPE_ICON.get(p.get("type", "skill"), "")
            print(f"{i}. {icon} {pick.get('name')}  [{tlabel}]  ({p.get('domain')}/{p.get('subcategory')})")
            print(f"   เหตุผล: {pick.get('why')}")
            if p.get("url"):
                print(f"   {p.get('url')}")
            print()
        if verdict:
            conf = verdict.get("confidence", "?")
            conf_icon = {"high": "🟢", "medium": "🟡", "low": "🔴"}.get(conf, "")
            print(f"   {conf_icon} ความมั่นใจ: {conf}")
            gap = verdict.get("gap", "")
            if gap and gap != "ครบแล้ว":
                print(f"   ⚠️ ยังขาด: {gap}")
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
