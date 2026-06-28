"""`aim do "<งาน>"` — ครบวงจรอัตโนมัติ: route -> โหลด skill -> ลงมือทำ.

1. route (local + verify) หา capability ที่ใช่ที่สุด
2. ถ้า pick #1 เป็น skill -> ดึง SKILL.md (จาก GitHub raw) มาเป็นคำสั่ง
3. ส่ง task + คำสั่ง skill ให้ LLM ลงมือทำ -> คืนผลงาน

tool/agent/rag ทำเองอัตโนมัติไม่ได้ (ต้องเรียก tool/agent จริง) -> บอกผู้ใช้ว่าต้องใช้อะไร.
"""
from __future__ import annotations

import urllib.error
import urllib.request

from .llm import _chat
from .router import route


def _raw_url(url: str | None) -> str | None:
    """แปลง github blob URL -> raw.githubusercontent.com เพื่อดึงเนื้อไฟล์."""
    if not url or "github.com/" not in url or "/blob/" not in url:
        return None
    return (url.replace("https://github.com/", "https://raw.githubusercontent.com/")
               .replace("/blob/", "/"))


def _fetch(url: str, limit: int = 16000) -> str | None:
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "aim-do"})
        with urllib.request.urlopen(req, timeout=20) as resp:
            return resp.read().decode("utf-8", errors="replace")[:limit]
    except (urllib.error.URLError, OSError, ValueError):
        return None


def cmd_do(settings: dict, task: str, backend: str = "local") -> int:
    result = route(settings, task, top_k=3, use_llm=True, use_verify=True, backend=backend)
    picks = result.get("picks", [])
    if not picks:
        print(f"[aim] หา capability ที่เหมาะกับ \"{task}\" ไม่เจอ")
        return 1

    top = picks[0]
    name, ptype = top.get("name"), top.get("type", "skill")
    print(f"\n🎯 งาน: {task}")
    print(f"   เลือกใช้: {name} [{ptype}] — {top.get('why') or top.get('summary_th')}")
    if result.get("confidence"):
        print(f"   ความมั่นใจ router: {result['confidence']}")

    if ptype != "skill":
        kind = {"mcp-tool": "MCP tool", "agent": "subagent", "rag": "RAG collection"}.get(ptype, ptype)
        print(f"\n⚠️ งานนี้ต้องใช้ {kind} ('{name}') ซึ่งต้องเรียกผ่าน harness จริง — Aim ทำเองอัตโนมัติไม่ได้")
        print(f"   ดูที่: {top.get('url') or '(no url)'}")
        return 0

    raw = _raw_url(top.get("url"))
    skill_doc = _fetch(raw) if raw else None
    if not skill_doc:
        print(f"\n⚠️ โหลดคำสั่งของ skill '{name}' ไม่ได้ ({top.get('url')})")
        print("   ทำต่อด้วยคำอธิบายย่อแทน ...")
        skill_doc = top.get("summary_th") or name

    print(f"   ลงมือทำตามแนว '{name}' ...\n")
    prompt = (
        f"คุณกำลังทำงานโดยใช้สกิลนี้เป็นแนวทาง (ปฏิบัติตามอย่างเคร่งครัด):\n\n"
        f"=== SKILL: {name} ===\n{skill_doc}\n=== จบ SKILL ===\n\n"
        f"งานของผู้ใช้: \"{task}\"\n\n"
        f"ลงมือทำงานนี้ให้เสร็จเป็นผลงานจริงที่ส่งมอบได้ทันที ตามแนวทางของสกิลข้างบน "
        f"ตอบเป็นภาษาไทย กระชับ ใช้งานได้จริง ไม่ต้องอธิบายว่าจะทำอะไร — ทำเลย."
    )
    output = _chat(settings, prompt)
    if output is None:
        print("[aim] LLM ไม่ตอบ (เช็ก OPENROUTER_API_KEY / AIM_SECRETS_FILE)")
        return 1

    print("─" * 60)
    print(output.strip())
    print("─" * 60)
    return 0
