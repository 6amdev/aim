"""M3 router — รับงานเป็นข้อความ -> semantic search -> top-N capability ที่ใช่.

embed query ด้วยโมเดลเดียวกับตอน index (all-MiniLM-L6-v2, 384d) แล้วค้นใน Qdrant.
รองรับ --json เพื่อให้ AI/สคริปต์อ่านผลแล้วทำงานต่อเองได้.
"""
from __future__ import annotations

import json

from .index import MODEL_NAME, _req

_TIER_ICON = {"must-have": "🟢", "nice-to-have": "🟡", "niche": "⚪"}
_TYPE_ICON = {"skill": "📄 skill", "mcp-tool": "🛠️ tool", "agent": "🤖 agent", "rag": "📚 rag"}


def _search(settings: dict, task: str, limit: int, harness: str | None,
            backend: str) -> list[dict]:
    if backend == "local":
        from .local_store import local_search
        return local_search(task, limit, settings, harness)

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
    return _req(f"{base}/collections/{coll}/points/search", body, method="POST").get("result", [])


def route(settings: dict, task: str, top_k: int = 5, harness: str | None = None,
          use_llm: bool = False, use_verify: bool = False,
          backend: str = "qdrant") -> dict:
    """หัวใจของ router — คืน dict ผลลัพธ์ (ไม่ print). ใช้ได้ทั้ง CLI และเรียกตรงจากโค้ด/AI."""
    if use_verify:
        use_llm = True  # verify ต้องมี picks จาก re-rank ก่อน

    limit = max(top_k * 2, 12) if use_llm else top_k
    hits = _search(settings, task, limit, harness, backend)
    by_name = {h.get("payload", {}).get("name"): h.get("payload", {}) for h in hits}

    result: dict = {"task": task, "backend": backend, "reranked": False,
                    "verified": False, "confidence": None, "gap": None, "picks": []}

    picks = None
    if use_llm:
        from .llm import rerank
        picks = rerank(settings, task, hits, top_k)

    if picks:
        result["reranked"] = True
        if use_verify:
            from .llm import verify
            verdict = verify(settings, task, picks, by_name)
            if verdict:
                result["verified"] = True
                result["confidence"] = verdict.get("confidence")
                result["gap"] = verdict.get("gap")
                keep = set(verdict.get("verified") or [])
                if keep:
                    picks = [p for p in picks if p.get("name") in keep] or picks

        for i, pick in enumerate(picks, 1):
            p = by_name.get(pick.get("name"), {})
            result["picks"].append({
                "rank": i, "name": pick.get("name"), "why": pick.get("why"),
                "type": p.get("type", "skill"), "tier": p.get("tier"),
                "domain": p.get("domain"), "subcategory": p.get("subcategory"),
                "summary_th": p.get("summary_th"), "url": p.get("url"), "score": None,
            })
        return result

    # vector order (ไม่มี LLM หรือ re-rank พัง)
    for i, h in enumerate(hits[:top_k], 1):
        p = h.get("payload", {})
        result["picks"].append({
            "rank": i, "name": p.get("name"), "why": None,
            "type": p.get("type", "skill"), "tier": p.get("tier"),
            "domain": p.get("domain"), "subcategory": p.get("subcategory"),
            "summary_th": p.get("summary_th"), "url": p.get("url"),
            "score": round(h.get("score"), 3) if h.get("score") is not None else None,
        })
    return result


def _render(result: dict) -> None:
    print(f"\n🎯 งาน: {result['task']}  [{result['backend']}]")
    picks = result["picks"]
    if result["reranked"]:
        label = "LLM re-ranked + verified" if result["verified"] else "LLM re-ranked"
        print(f"   แนะนำ {len(picks)} capability ({label}):\n")
    else:
        print(f"   แนะนำ {len(picks)} capability ที่ใช่ที่สุด:\n")

    for pick in picks:
        icon = _TIER_ICON.get(pick.get("tier"), "")
        tlabel = _TYPE_ICON.get(pick.get("type", "skill"), "")
        score = f"  ~{pick['score']:.3f}" if pick.get("score") is not None else ""
        print(f"{pick['rank']}. {icon} {pick.get('name')}  [{tlabel}]  ({pick.get('domain')}/{pick.get('subcategory')}){score}")
        if pick.get("why"):
            print(f"   เหตุผล: {pick['why']}")
        elif pick.get("summary_th"):
            print(f"   {pick['summary_th']}")
        if pick.get("url"):
            print(f"   {pick['url']}")
        print()

    if result["verified"]:
        conf = result.get("confidence") or "?"
        conf_icon = {"high": "🟢", "medium": "🟡", "low": "🔴"}.get(conf, "")
        print(f"   {conf_icon} ความมั่นใจ: {conf}")
        gap = result.get("gap")
        if gap and gap != "ครบแล้ว":
            print(f"   ⚠️ ยังขาด: {gap}")


def cmd_route(settings: dict, task: str, top_k: int = 5,
              harness: str | None = None, use_llm: bool = False,
              use_verify: bool = False, backend: str = "qdrant",
              as_json: bool = False) -> int:
    result = route(settings, task, top_k, harness, use_llm, use_verify, backend)
    if as_json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        _render(result)
    return 0
