# AI Quality Harness — Design Spec

> สถานะ: design (รอ wit รีวิว) · วันที่ 2026-06-27 · เจ้าของ: wit
> โปรเจคใหม่ ต่อยอดจาก [skills-catalog](2026-06-27-skills-catalog-design.md)

## 1. เป้าหมาย (north star)
ระบบที่รับงานเข้ามาแล้วทำให้ AI ผลิตผลงาน **คุณภาพสูงสุด + ตรงเป้า** โดย **คนใช้งานง่าย** (ไม่ต้องรู้เบื้องหลังว่ามี skill/tool/RAG อะไร)

แตกเป็น 3 เสา:
| เสา | วัดยังไง | กลไกหลัก |
|-----|---------|---------|
| **ตรงเป้า** | เลือกเครื่องมือ/ความรู้ที่ใช่กับงาน | **router** + RAG + tools |
| **คุณภาพสูงสุด** | ผลงานเชื่อถือได้ ผ่านการตรวจ | **verify** (multi-agent/self-critique) + evals |
| **ใช้งานง่าย** | สั่งงานเป็นภาษาคน | **front door** (interface-agnostic) |

## 2. หลักการออกแบบ
- **Core เป็นกลาง ไม่ผูก interface** — ตรรกะอยู่ที่ core เดียว, หน้าบ้าน (Claude Code/Telegram/เว็บ) เป็นแค่ adapter บางๆ
- **ต่อยอดของที่มี ไม่สร้างใหม่** — Qdrant (ค้นหา), qdrant-mcp, OpenRouter (LLM), OpenClaw (harness Ollama), catalog 126 ตัว
- **เล็กก่อน โตทีหลัง** — MVP = router อย่างเดียว เห็นผลแล้วค่อยเติม verify → front door อื่น
- **Capability ไม่ใช่แค่ skill** — index ทุกชนิด (skill/tool/RAG/agent) ให้ router เลือกข้ามชนิดได้

## 3. สถาปัตยกรรม
```
หน้าบ้าน (Claude Code ก่อน · Telegram/เว็บ ทีหลัง)
        ↓  งานเป็นภาษาคน
[ front door ]  ← phase 3
        ↓
[ router ]  ── qdrant-find ──► capability_catalog (ใน Qdrant)
        ↓  เลือก top-N capability ที่ใช่ + เหตุผล
[ ลงมือทำ ]  ── skills / MCP tools / RAG / subagents
        ↓
[ verify ]  ← phase 2  ตรวจ/ขัดเกลาก่อนส่ง
        ↓
ผลงานคุณภาพ + บอกที่มา (ใช้ capability อะไรไปบ้าง)
```

## 4. คอมโพเนนต์

### 4.1 Capability Catalog (ข้อมูล — ต่อยอดจาก skills-catalog)
ขยาย `skills-catalog/data/catalog.json` ให้แต่ละ entry มี field เพิ่ม:
- `type`: `skill` | `mcp-tool` | `rag` | `agent` | `command`
- `harness`: `claude` | `ollama` | `both`  (skill บางตัวผูก Claude — กันแนะนำผิด)
- `when_to_use`: 1 ประโยค "ใช้ตอนงานแบบไหน" (ใช้เป็น text ฝัง embedding)
ตอนนี้มี 126 `skill` แล้ว → phase หลังเติม mcp-tool ของ wit (media/content/qdrant), RAG collections, agents 17 คน

### 4.2 Indexer (`ai-harness/index.py`)
อ่าน catalog → สร้าง text สำหรับฝัง (`name + when_to_use + summary_th + subcategory`) → upsert เข้า Qdrant collection **`capability_catalog`** ผ่าน qdrant-mcp/REST
- รันซ้ำได้ (idempotent ตาม id) · payload เก็บ field ทั้งหมดไว้ filter (เช่น `harness=claude`)

### 4.3 Router (`ai-harness/router.py`) ← **MVP หลัก**
รับ task เป็นข้อความ → `qdrant-find` semantic search → คืน **top-N capability ที่ใช่ + เหตุผล + วิธีใช้**
- input: `task` (str), optional `harness` filter, `top_k`
- ขั้นตอน: embed task → search → (option) LLM re-rank ด้วย OpenRouter ให้จัดอันดับ + เขียนเหตุผลไทย
- output: รายการ `{name, type, why, how_to_use, score}` + คำแนะนำว่า "งานนี้ควรใช้ X ก่อน แล้วเสริม Y"

### 4.4 Verify (phase 2)
"quality recipe" — หลังทำงานเสร็จ ส่งผลให้ verifier ตรวจก่อนคืน
- เริ่มจาก self-critique 1 รอบ → ต่อยอดเป็น multi-agent adversarial (เหมือนที่เราใช้ตอน research)
- กำหนด "เกณฑ์คุณภาพ" ต่อชนิดงาน (เช่น โค้ด=เทสต์ผ่าน, คอนเทนต์=ตรง brief)

### 4.5 Front door (phase 3)
core เดียว เปิดผ่านหลาย adapter:
- **Claude Code** (MVP): เป็น skill/command `/route <งาน>`
- **Telegram**: ต่อผ่าน OpenClaw bot ที่มีอยู่
- **เว็บ**: REST endpoint บางๆ (ทีหลัง)

## 5. ใช้ของเดิมยังไง
| ต้องใช้ | ของที่ wit มีแล้ว |
|--------|------------------|
| ค้นหา semantic | Qdrant + qdrant-mcp (FastEmbed MiniLM 384d) |
| LLM re-rank/verify | OpenRouter (claude-sonnet) — key ใน `secrets/all-keys.env` |
| harness รัน Ollama | OpenClaw (สำหรับ adapter Telegram) |
| คลังความสามารถ | skills-catalog (126 + ขยายต่อ) |

## 6. MVP — ขอบเขตที่ทำก่อน (เล็กสุดที่ใช้ได้จริง)
**= Indexer + Router + ใช้ผ่าน Claude Code**
1. ขยาย catalog เพิ่ม `type/harness/when_to_use` (skills เดิม 126)
2. index เข้า Qdrant `capability_catalog`
3. router: พิมพ์งาน → คืน top-5 capability + เหตุผลไทย
4. ใช้ผ่าน command/skill บน Claude Code
**ยังไม่ทำใน MVP:** verify, Telegram/เว็บ, tool/agent indexing (เติม phase ถัดไป)

## 7. Roadmap (phase)
- **P1 (MVP):** catalog+type → index → router → Claude Code
- **P2:** เพิ่ม capability ชนิดอื่น (tools/RAG/agents) เข้า index
- **P3:** verify (self-critique → multi-agent)
- **P4:** front door อื่น (Telegram ผ่าน OpenClaw, เว็บ)
- **P5:** evals — วัดว่า router/verify แนะนำดีจริง แล้วปรับ

## 8. การตัดสิน (open questions ที่เคลียร์แล้ว)
| ประเด็น | ตัดสิน |
|--------|-------|
| ภาษา/stack | Python (ตาม home-lab) ต่อ Qdrant REST + OpenRouter |
| collection | ใหม่ `capability_catalog` (แยกจาก homelab_knowledge/news_daily) |
| embedding | ใช้ FastEmbed MiniLM 384d เดิม (ผ่าน qdrant-mcp) ให้ทั้งระบบ dim ตรงกัน |
| LLM re-rank | ทำเป็น option (`--no-llm` ใช้ vector อย่างเดียว, เปิด LLM เพื่อเหตุผล/จัดอันดับ) |
| รันที่ไหน | local Windows ได้ (ต่อ Qdrant ผ่าน 127.0.0.1 หรือ SSH tunnel) |

## 9. ความเสี่ยง
1. **router แนะนำมั่ว** ถ้า `when_to_use` เขียนไม่ดี → ลงทุนเขียน when_to_use ให้คม (เป็น text ที่ embedding ใช้จริง)
2. **dim embedding ไม่ตรง** ระหว่าง index กับ query → บังคับใช้ตัวเดียว (MiniLM 384d) ทั้งระบบ
3. **บานปลาย** — ยึด MVP P1 ให้จบก่อน ห้ามกระโดดไป verify/เว็บ
4. **Qdrant เข้าถึงจากนอก** — service bind 127.0.0.1 (lockdown) → รัน indexer/router บน server หรือผ่าน tunnel
