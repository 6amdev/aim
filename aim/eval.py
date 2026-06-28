"""P5 evals — วัดว่า router แนะนำ capability ที่ใช่จริงไหม.

อ่าน data/evals.json (task -> expect[]) รัน router ทุกเคส แล้วรายงาน
hit@1/3/5 + MRR. ใช้ local backend เป็นค่าเริ่มต้น (ไม่ต้องเปิด server).
เปิด --llm เพื่อวัดผลหลัง LLM re-rank ด้วย.
"""
from __future__ import annotations

import json

from .index import DATA_PATH

EVALS_PATH = DATA_PATH.parent / "evals.json"


def _ranked_names(settings: dict, task: str, limit: int, use_llm: bool,
                  backend: str) -> list[str]:
    """คืนรายชื่อ capability เรียงตามอันดับที่ router จะแนะนำ."""
    if backend == "local":
        from .local_store import local_search
        hits = local_search(task, max(limit * 2, 12) if use_llm else limit, settings, None)
    else:
        from fastembed import TextEmbedding
        from .index import MODEL_NAME, _req
        base = settings["qdrant_url"].rstrip("/")
        coll = settings["collection"]
        qvec = list(TextEmbedding(model_name=MODEL_NAME).embed([task]))[0].tolist()
        body = {"vector": qvec, "limit": max(limit * 2, 12) if use_llm else limit,
                "with_payload": True}
        hits = _req(f"{base}/collections/{coll}/points/search", body, method="POST").get("result", [])

    if use_llm:
        from .llm import rerank
        picks = rerank(settings, task, hits, limit)
        if picks:
            return [p.get("name") for p in picks]
        # rerank พัง -> ตกลงมาใช้ vector order

    return [h.get("payload", {}).get("name") for h in hits[:limit]]


def _first_hit_rank(ranked: list[str], expect: list[str]) -> int | None:
    """อันดับ (1-based) ของตัวแรกใน ranked ที่ตรง expect; None ถ้าไม่เจอ."""
    want = set(expect)
    for i, name in enumerate(ranked, 1):
        if name in want:
            return i
    return None


def cmd_eval(settings: dict, top_k: int = 5, use_llm: bool = False,
             backend: str = "local", verbose: bool = False) -> int:
    if not EVALS_PATH.exists():
        print(f"[aim] ไม่พบ {EVALS_PATH}")
        return 1
    cases = json.loads(EVALS_PATH.read_text(encoding="utf-8")).get("cases", [])
    if not cases:
        print(f"[aim] {EVALS_PATH} ไม่มีเคส")
        return 1

    label = "local" if backend == "local" else "qdrant"
    mode = "vector + LLM re-rank" if use_llm else "vector only"
    print(f"\n📊 Aim eval — {len(cases)} เคส  [{label} · {mode} · top-{top_k}]\n")

    hit1 = hit3 = hit5 = 0
    rr_sum = 0.0
    misses: list[tuple[str, list[str]]] = []

    for case in cases:
        task = case["task"]
        expect = case["expect"]
        ranked = _ranked_names(settings, task, top_k, use_llm, backend)
        rank = _first_hit_rank(ranked, expect)

        if rank is not None:
            rr_sum += 1.0 / rank
            if rank <= 1:
                hit1 += 1
            if rank <= 3:
                hit3 += 1
            if rank <= 5:
                hit5 += 1
            mark = "🟢" if rank == 1 else ("🟡" if rank <= 3 else "⚪")
            detail = f"{mark} #{rank}"
        else:
            misses.append((task, expect))
            detail = "🔴 miss"

        if verbose:
            print(f"  {detail:>8}  {task}")
            if rank != 1:
                print(f"            ↳ got: {', '.join(ranked[:3])}")

    n = len(cases)
    print(f"\n  hit@1 : {hit1}/{n}  ({hit1/n:.0%})")
    print(f"  hit@3 : {hit3}/{n}  ({hit3/n:.0%})")
    print(f"  hit@5 : {hit5}/{n}  ({hit5/n:.0%})")
    print(f"  MRR   : {rr_sum/n:.3f}")

    if misses:
        print(f"\n  🔴 miss ({len(misses)}):")
        for task, expect in misses:
            print(f"     - {task}  (อยาก: {', '.join(expect)})")

    print()
    return 0
