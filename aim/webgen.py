"""web — gen หน้าเว็บ browse capability จาก catalog.json.

self-contained HTML ไฟล์เดียว (embed data + vanilla JS) เปิดตรงๆ ในเบราว์เซอร์
ได้เลย ไม่ต้อง server. มี search + filter domain/type + การ์ดรายละเอียด.
"""
from __future__ import annotations

import json

from .index import DATA_PATH

OUT_PATH = DATA_PATH.parent.parent / "docs" / "catalog.html"

_HTML = """<!doctype html>
<html lang="th">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Aim — Capability Catalog</title>
<style>
  :root {{ color-scheme: light dark; --bg:#0f1115; --card:#1a1d24; --fg:#e7e9ee;
           --mut:#9aa0ad; --line:#2a2f3a; --accent:#6ea8fe; }}
  @media (prefers-color-scheme: light) {{
    :root {{ --bg:#f6f7f9; --card:#fff; --fg:#1a1d24; --mut:#5a616e; --line:#e2e5ea; --accent:#2f6fed; }}
  }}
  * {{ box-sizing:border-box; }}
  body {{ margin:0; background:var(--bg); color:var(--fg);
          font:15px/1.5 system-ui,-apple-system,"Segoe UI",Roboto,sans-serif; }}
  header {{ position:sticky; top:0; background:var(--bg); border-bottom:1px solid var(--line);
            padding:14px 20px; z-index:10; }}
  h1 {{ margin:0 0 10px; font-size:20px; }}
  h1 small {{ color:var(--mut); font-weight:400; font-size:14px; }}
  .controls {{ display:flex; gap:8px; flex-wrap:wrap; align-items:center; }}
  input, select {{ background:var(--card); color:var(--fg); border:1px solid var(--line);
                   border-radius:8px; padding:8px 10px; font-size:14px; }}
  input#q {{ flex:1; min-width:200px; }}
  .grid {{ display:grid; grid-template-columns:repeat(auto-fill,minmax(320px,1fr));
           gap:12px; padding:18px 20px; }}
  .card {{ background:var(--card); border:1px solid var(--line); border-radius:12px; padding:14px; }}
  .card h3 {{ margin:0 0 6px; font-size:16px; display:flex; align-items:center; gap:8px; }}
  .badge {{ font-size:11px; padding:2px 7px; border-radius:20px; border:1px solid var(--line);
            color:var(--mut); white-space:nowrap; }}
  .meta {{ color:var(--mut); font-size:12px; margin:4px 0 8px; }}
  .card p {{ margin:6px 0; }}
  .wtu {{ font-size:13px; color:var(--mut); border-left:2px solid var(--line); padding-left:8px; }}
  a {{ color:var(--accent); text-decoration:none; font-size:13px; }}
  a:hover {{ text-decoration:underline; }}
  .empty {{ padding:40px 20px; color:var(--mut); text-align:center; }}
</style>
</head>
<body>
<header>
  <h1>🎯 Aim Capability Catalog <small id="count"></small></h1>
  <div class="controls">
    <input id="q" placeholder="ค้นหา… (ชื่อ / คำอธิบาย / when_to_use)">
    <select id="domain"><option value="">ทุก domain</option></select>
    <select id="type">
      <option value="">ทุกชนิด</option>
      <option value="skill">📄 skill</option>
      <option value="mcp-tool">🛠️ tool</option>
      <option value="agent">🤖 agent</option>
      <option value="rag">📚 rag</option>
    </select>
    <select id="sort">
      <option value="name">เรียง: ชื่อ</option>
      <option value="stars">เรียง: ดาว</option>
      <option value="domain">เรียง: domain</option>
    </select>
  </div>
</header>
<div id="grid" class="grid"></div>
<script>
const DATA = {data};
const TYPE = {{skill:"📄 skill","mcp-tool":"🛠️ tool",agent:"🤖 agent",rag:"📚 rag"}};
const $ = s => document.querySelector(s);
const domains = [...new Set(DATA.map(d=>d.domain))].sort();
$("#domain").insertAdjacentHTML("beforeend",
  domains.map(d=>`<option value="${{d}}">${{d}}</option>`).join(""));

function esc(s) {{ return (s||"").replace(/[&<>]/g, c=>({{"&":"&amp;","<":"&lt;",">":"&gt;"}}[c])); }}

function render() {{
  const q = $("#q").value.trim().toLowerCase();
  const dom = $("#domain").value, typ = $("#type").value, sort = $("#sort").value;
  let rows = DATA.filter(d => {{
    if (dom && d.domain!==dom) return false;
    if (typ && (d.type||"skill")!==typ) return false;
    if (q) {{
      const hay = (d.name+" "+(d.summary_th||"")+" "+(d.when_to_use||"")+" "+(d.subcategory||"")).toLowerCase();
      if (!hay.includes(q)) return false;
    }}
    return true;
  }});
  rows.sort((a,b)=> sort==="stars" ? (b.stars||0)-(a.stars||0)
                  : sort==="domain" ? (a.domain||"").localeCompare(b.domain||"") || a.name.localeCompare(b.name)
                  : a.name.localeCompare(b.name));
  $("#count").textContent = `— ${{rows.length}}/${{DATA.length}}`;
  $("#grid").innerHTML = rows.length ? rows.map(d=>`
    <div class="card">
      <h3>${{esc(d.name)}} <span class="badge">${{TYPE[d.type]||d.type||"skill"}}</span></h3>
      <div class="meta">${{esc(d.domain)}} / ${{esc(d.subcategory||"")}} · ${{d.tier||""}} ${{d.stars?("· ⭐"+d.stars):""}}</div>
      <p>${{esc(d.summary_th||"")}}</p>
      ${{d.when_to_use && d.when_to_use!==d.summary_th ? `<p class="wtu">เมื่อไร: ${{esc(d.when_to_use)}}</p>`:""}}
      ${{d.url ? `<a href="${{esc(d.url)}}" target="_blank" rel="noopener">source ↗</a>`:""}}
    </div>`).join("") : `<div class="empty">ไม่พบ capability ที่ตรงเงื่อนไข</div>`;
}}
["#q","#domain","#type","#sort"].forEach(s=>$(s).addEventListener("input",render));
render();
</script>
</body>
</html>
"""


def cmd_web(settings: dict) -> int:
    caps = json.loads(DATA_PATH.read_text(encoding="utf-8")).get("capabilities", [])
    if not caps:
        print(f"[aim] no capabilities in {DATA_PATH}")
        return 1
    # เก็บเฉพาะ field ที่หน้าเว็บใช้ (ลดขนาดไฟล์)
    keep = ("name", "type", "domain", "subcategory", "summary_th",
            "when_to_use", "url", "stars", "tier")
    slim = [{k: c.get(k) for k in keep} for c in caps]
    html = _HTML.format(data=json.dumps(slim, ensure_ascii=False))
    OUT_PATH.write_text(html, encoding="utf-8")
    print(f"[aim] เขียนหน้าเว็บ -> {OUT_PATH}  ({len(caps)} capability)")
    print(f"[aim] เปิดดู: start {OUT_PATH}")
    return 0
