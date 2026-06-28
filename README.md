# 🎯 Aim

> ระบบที่รับงานเป็นภาษาคน แล้วทำให้ AI ผลิตผลงาน **คุณภาพสูงสุด + ตรงเป้า** โดย **ใช้งานง่าย**
> *Aim a task at the right capabilities, hit the target with quality.*

Aim เป็น **quality harness / capability router** — รับคำสั่งงาน → เลือก skill/tool/RAG/agent ที่ใช่ให้อัตโนมัติ → คุมคุณภาพก่อนส่งผลลัพธ์ โดยต่อยอดจากของที่มีอยู่แล้ว (Qdrant, MCP, OpenRouter, catalog 126+ skills)

## 3 เสาหลัก
| เสา | ความหมาย | กลไก |
|-----|---------|------|
| 🎯 ตรงเป้า | เลือกเครื่องมือที่ใช่กับงาน | router (semantic search บน Qdrant) |
| ⭐ คุณภาพสูงสุด | ผลงานเชื่อถือได้ ผ่านการตรวจ | verify (self-critique → multi-agent) |
| 🙂 ใช้งานง่าย | สั่งงานเป็นภาษาคน | front door (interface-agnostic) |

## สถาปัตยกรรม
```
หน้าบ้าน (Claude Code ก่อน · Telegram/เว็บ ทีหลัง)
   ↓ งานภาษาคน
[front door] → [router] ──qdrant-find──► capability_catalog (Qdrant)
                 ↓ top-N capability ที่ใช่ + เหตุผล
            [ลงมือทำ] skills / MCP tools / RAG / subagents
                 ↓
            [verify] ตรวจก่อนส่ง
                 ↓
        ผลงานคุณภาพ + บอกที่มา
```

## สถานะ
✅ **P1–P3 เสร็จ + Local mode**: router (192 capabilities: skill/tool/agent/rag) → LLM re-rank → verify (confidence + gap)
ดูรายละเอียด: [docs/design.md](docs/design.md) · [docs/plan.md](docs/plan.md)

## ใช้งาน
**Local (ในเครื่อง — ไม่ต้องเปิด server):** clone มาแล้วรันได้เลย — runner ตั้ง venv + index ให้เองครั้งแรก
```powershell
powershell -File route.local.ps1 -Task "ทำคลิป TikTok รีวิว gadget"
powershell -File route.local.ps1 -Task "<งาน>" -Json   # ผลเป็น JSON ให้ AI/สคริปต์อ่านต่อ
```
หรือพิมพ์ `/route <งาน>` ใน Claude Code (เรียก route.local.ps1 ให้)

**ให้ AI เรียกเอง:** `route(settings, task, ..., backend="local")` ใน [aim/router.py](aim/router.py) คืน dict ผลลัพธ์โดยตรง (ไม่ print) — หรือใช้ CLI `--json`

**วัดคุณภาพ router:** `python -m aim eval` (hit@k + MRR บน [data/evals.json](data/evals.json) 30 เคส)

**Server (สำหรับบริการ 24 ชม. — Telegram/เว็บ ทีหลัง):** `ssh home '/mnt/data/projects/aim/route.sh "<งาน>"'`

## Roadmap
- **P1 (MVP)**: catalog+type → index เข้า Qdrant → router → `/route` บน Claude Code
- **P2**: เพิ่ม capability ชนิด tool/RAG/agent เข้า index
- **P3**: verify (self-critique → multi-agent adversarial)
- **P4**: front door อื่น (Telegram ผ่าน OpenClaw, เว็บ REST)
- **P5**: evals — วัดว่า router/verify แนะนำดีจริง

## ใช้ของเดิม (ไม่สร้างใหม่)
Qdrant + qdrant-mcp (ค้นหา) · OpenRouter claude-sonnet (re-rank/verify) · OpenClaw (harness Ollama) · [skills-catalog](../home-lab/skills-catalog) (คลังความสามารถ 126+)

## Stack
Python · Qdrant REST · OpenRouter API · FastEmbed MiniLM (384d)
