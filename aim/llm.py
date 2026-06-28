"""M4 — LLM re-rank candidates ผ่าน OpenRouter (claude-sonnet).

เอา candidate จาก vector search ส่งให้ LLM จัดอันดับใหม่ + กรองที่ไม่เกี่ยว
+ เขียนเหตุผลสั้นภาษาไทย. ถ้าไม่มี key / call พัง -> คืน None (router ใช้ vector order แทน).
"""
from __future__ import annotations

import json
import urllib.error
import urllib.request


def _chat(settings: dict, prompt: str) -> str | None:
    """เรียก OpenRouter chat 1 ครั้ง คืน content (str) หรือ None ถ้าไม่มี key/พัง."""
    key = settings.get("openrouter_key")
    if not key:
        return None
    base = settings["openrouter_base"].rstrip("/")
    body = json.dumps({
        "model": settings["model"],
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
        return data["choices"][0]["message"]["content"]
    except urllib.error.HTTPError as exc:
        print(f"[aim] LLM ข้าม (HTTP {exc.code} จาก model '{settings['model']}')")
        return None
    except Exception as exc:  # noqa: BLE001
        print(f"[aim] LLM ข้าม ({type(exc).__name__})")
        return None


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
        f"สำคัญ: ถ้างานคือการ \"ลงมือผลิตผลงาน\" (เขียน/ทำ/สร้าง/ออกแบบ) ให้จัด capability ที่ "
        f"\"ลงมือทำชิ้นงานนั้นจริง\" ไว้อันดับต้น เหนือตัวที่แค่ \"วางแผน/บรีฟ/วิเคราะห์/เป็นเอเจนต์\".\n"
        f"ตอบเป็น JSON เท่านั้น: {{\"picks\":[{{\"name\":\"<ชื่อตรงเป๊ะ>\",\"why\":\"<เหตุผลไทย>\"}}]}}"
    )

    content = _chat(settings, prompt)
    if content is None:
        print("[aim] re-rank ข้าม — ใช้ vector order แทน")
        return None
    try:
        return json.loads(_strip_fences(content)).get("picks", [])
    except Exception:  # noqa: BLE001
        return None


def verify(settings: dict, task: str, picks: list[dict], payloads: dict) -> dict | None:
    """ตรวจคำแนะนำแบบ adversarial: กรองตัวไม่เกี่ยว + ความมั่นใจ + gap.
    คืน {"verified":[name...], "confidence":"high|medium|low", "gap":"..."} หรือ None."""
    if not picks:
        return None
    listed = []
    for p in picks:
        meta = payloads.get(p.get("name"), {})
        listed.append(f"- {p.get('name')} [{meta.get('type','skill')} · {meta.get('subcategory','')}]: {meta.get('summary_th','')}")
    block = "\n".join(listed)
    prompt = (
        f"งานของผู้ใช้: \"{task}\"\n\n"
        f"ระบบแนะนำ capability เหล่านี้:\n{block}\n\n"
        f"ทำหน้าที่ตรวจสอบแบบเข้มงวด (adversarial):\n"
        f"1. ตัวไหน \"ไม่เกี่ยวกับงานนี้จริง\" ให้คัดออก เหลือเฉพาะที่เกี่ยวจริง\n"
        f"2. ประเมินความมั่นใจรวมว่าคำแนะนำครอบคลุมงานแค่ไหน: high/medium/low\n"
        f"3. ระบุ gap: งานนี้ต้องการความสามารถอะไรที่ \"ไม่มีในรายการ\" บ้าง (ถ้าครบดีแล้วใส่ 'ครบแล้ว')\n"
        f"ตอบ JSON เท่านั้น: {{\"verified\":[\"<ชื่อที่เก็บไว้>\"],\"confidence\":\"high|medium|low\",\"gap\":\"<ไทย>\"}}"
    )
    content = _chat(settings, prompt)
    if content is None:
        return None
    try:
        return json.loads(_strip_fences(content))
    except Exception:  # noqa: BLE001
        return None
