# AI Quality Harness — Implementation Plan

> คู่กับ [design spec](2026-06-27-ai-harness-design.md) · MVP-first, ทำทีละชิ้นจบในตัว

## หลักคิด
ทำ **P1 (MVP) ให้จบก่อน** = พิมพ์งาน → ได้คำแนะนำ capability ที่ใช่ ห้ามกระโดดไป verify/เว็บ เพราะนั่นคือสาเหตุที่ทำให้งง

## P1 — MVP Router (โฟกัสตอนนี้)

| M | Goal | ไฟล์ | Exit criterion |
|---|------|------|---------------|
| **M0** | scaffold + ต่อ Qdrant ได้ | `ai-harness/config.py`, `requirements.txt` | รัน `python -m ai_harness ping` แล้ว Qdrant ตอบ healthy |
| **M1** | ขยาย catalog schema | แก้ `skills-catalog/data/catalog.json` (+`type/harness/when_to_use`) | 126 entry มี 3 field ครบ, JSON valid |
| **M2** | indexer เข้า Qdrant | `ai-harness/index.py` | `python -m ai_harness index` → collection `capability_catalog` มี 126 points |
| **M3** | router (vector อย่างเดียว) | `ai-harness/router.py` | `route "ทำคลิป TikTok"` → คืน top-5 มี clipify/video อยู่ในนั้น |
| **M4** | LLM re-rank + เหตุผลไทย | เพิ่มใน `router.py` (`--llm`) | เปิด `--llm` แล้วได้เหตุผลไทย + จัดอันดับใหม่ที่สมเหตุผล |
| **M5** | ใช้ผ่าน Claude Code | `.claude/commands/route.md` หรือ skill | พิมพ์ `/route <งาน>` ใน Claude Code แล้วได้คำแนะนำ |

## P1 dependency
M0 → M1 → M2 → M3 → M4 → M5 (เป็นเส้นตรง แต่ละ M ทดสอบได้เดี่ยว)

## รายละเอียด 3 step แรก

### M0 — ต่อ Qdrant
- `config.py`: อ่าน Qdrant URL + OpenRouter key จาก `secrets/all-keys.env`; รองรับ 127.0.0.1 หรือ SSH tunnel ไป `192.168.80.203`
- `python -m ai_harness ping` → GET `/healthz` ของ Qdrant → print ok/collections
- **test:** mock HTTP → ping คืน healthy; เชื่อมจริงครั้งเดียวยืนยัน

### M1 — ขยาย catalog
- เขียน migration เล็กๆ เติม `type:"skill"`, `harness` (เดา: ตัวที่ path เป็น anthropics/.claude → both, อื่น → claude), `when_to_use` (เริ่มจาก copy summary_th แล้วค่อยขัด)
- **test:** ทุก entry มี 3 field, enum ถูก, JSON ยัง valid (นับ 126)

### M2 — indexer
- อ่าน catalog → text = `name + when_to_use + summary_th + subcategory` → embed → upsert Qdrant (id = name+source hash)
- ใช้ FastEmbed MiniLM 384d ให้ตรงกับ qdrant-mcp เดิม
- idempotent: รันซ้ำไม่เพิ่มซ้ำ
- **test:** index fixture 3 ตัว → 3 points; รันซ้ำยัง 3 points

## Phase ถัดไป (ยังไม่ทำ — กันบานปลาย)
- **P2:** เติม capability ชนิด tool/RAG/agent เข้า catalog + index
- **P3:** verify (self-critique → multi-agent adversarial เหมือนที่ใช้ตอน research)
- **P4:** front door Telegram (ผ่าน OpenClaw) + เว็บ REST
- **P5:** evals วัดคุณภาพ router/verify

## ความเสี่ยงเชิงปฏิบัติ
- เขียน `when_to_use` ให้คม = ตัวชี้ขาดคุณภาพ router (embedding ใช้ field นี้เป็นหลัก)
- บังคับ embedding ตัวเดียว (MiniLM 384d) ทั้ง index + query กัน dim ไม่ตรง
- Qdrant bind 127.0.0.1 → รัน indexer บน server หรือเปิด SSH tunnel ตอน dev บน Windows
- **วินัย:** จบ M5 (พิมพ์งานได้คำแนะนำ) ก่อนแตะ P2+
