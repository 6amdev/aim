"""M4 — LLM re-rank candidates ผ่าน OpenRouter (claude-sonnet).

เอา candidate จาก vector search ส่งให้ LLM จัดอันดับใหม่ + กรองที่ไม่เกี่ยว
+ เขียนเหตุผลสั้นภาษาไทย. ถ้าไม่มี key / call พัง -> คืน None (router ใช้ vector order แทน).
"""
from __future__ import annotations

import json
import urllib.error
import urllib.request


def _strip_fences(text: str) -> str:
    t = text.strip()
    if t.startswith("```"):
        t = t.split("\n", 1)[1] if "\n" in t else t
        if t.endswith("```"):
            t = t[: -3]
    return t.strip()


def rerank(settings: dict, task: str, candidates: list[dict], top_k: int) -> list[dict] | None:
    key = settings.get("openrouter_key")
    if not key:
        return None

    base = settings["openrouter_base"].rstrip("/")
    model = settings["model"]

    listed = []
    for c in candidates:
        p = c.get("payload", {})
        listed.append(f"- {p.get('name')} [{p.get('domain')}/{p.get('subcategory')}]: {p.get('summary_th')}")
    catalog_block = "\n".join(listed)

    prompt = (
        f"งานของผู้ใช้: \"{task}\"\n\n"
        f"นี่คือ capability ที่ค้นเจอ (ชื่อ [หมวด]: คำอธิบาย):\n{catalog_block}\n\n"
        f"เลือกที่ \"เกี่ยวกับงานจริงๆ\" สูงสุด {top_k} ตัว เรียงดีสุดก่อน ตัดที่ไม่เกี่ยวออก "
        f"พร้อมเหตุผลสั้นภาษาไทย (1 ประโยค) ว่าทำไมเหมาะกับงานนี้.\n"
        f"ตอบเป็น JSON เท่านั้น: {{\"picks\":[{{\"name\":\"<ชื่อตรงเป๊ะ>\",\"why\":\"<เหตุผลไทย>\"}}]}}"
    )

    body = json.dumps({
        "model": model,
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.2,
    }).encode()

    req = urllib.request.Request(
        f"{base}/chat/completions", data=body, method="POST",
        headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
    )
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            data = json.loads(resp.read().decode())
        content = data["choices"][0]["message"]["content"]
        parsed = json.loads(_strip_fences(content))
        return parsed.get("picks", [])
    except urllib.error.HTTPError as exc:
        print(f"[aim] LLM re-rank ข้าม (HTTP {exc.code} จาก model '{model}') — ใช้ vector order แทน")
        return None
    except Exception as exc:  # noqa: BLE001
        print(f"[aim] LLM re-rank ข้าม ({type(exc).__name__}) — ใช้ vector order แทน")
        return None
