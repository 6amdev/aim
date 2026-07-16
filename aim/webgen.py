"""web — gen หน้าเว็บ browse capability จาก catalog.json.

self-contained HTML ไฟล์เดียว (embed data + vanilla JS) เปิดตรงๆ ในเบราว์เซอร์
ได้เลย ไม่ต้อง server. ดีไซน์ technical control-panel: sidebar domain +
command-bar search + การ์ดรายละเอียด. ใช้ placeholder __DATA__ (ไม่ใช่ .format
เพื่อเลี่ยง escape brace ใน CSS/JS).
"""
from __future__ import annotations

import json

from .index import DATA_PATH

OUT_PATH = DATA_PATH.parent.parent / "docs" / "catalog.html"

_HTML = r"""<!doctype html>
<html lang="th">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Aim · Capability Catalog</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@400;500;600&family=IBM+Plex+Sans+Thai:wght@400;500;600;700&display=swap" rel="stylesheet">
<style>
  :root{
    --bg:#0a0c10; --panel:#101319; --card:#141922; --card2:#171d27;
    --line:#232a35; --fg:#e8ecf3; --mut:#828b9c; --dim:#5a6273;
    --accent:#ff5c37; --accent-soft:rgba(255,92,55,.14);
    --radius:14px; --mono:"IBM Plex Mono",ui-monospace,monospace;
    --sans:"IBM Plex Sans Thai","IBM Plex Sans",system-ui,sans-serif;
  }
  @media (prefers-color-scheme:light){
    :root{ --bg:#f4f2ee; --panel:#fbfaf8; --card:#ffffff; --card2:#faf9f6;
      --line:#e4e0d8; --fg:#1b1e24; --mut:#6b7280; --dim:#9aa0ab;
      --accent:#e23c17; --accent-soft:rgba(226,60,23,.10); }
  }
  *{ box-sizing:border-box; }
  html,body{ margin:0; }
  body{
    background:var(--bg); color:var(--fg); font-family:var(--sans);
    font-size:15px; line-height:1.55; -webkit-font-smoothing:antialiased;
    background-image:
      radial-gradient(60rem 60rem at 100% -10%, var(--accent-soft), transparent 55%),
      radial-gradient(50rem 50rem at -10% 110%, rgba(76,141,255,.08), transparent 55%);
    background-attachment:fixed;
  }
  a{ color:inherit; text-decoration:none; }

  /* layout */
  .wrap{ display:grid; grid-template-columns:250px 1fr; min-height:100vh; }
  aside{
    border-right:1px solid var(--line); background:color-mix(in srgb,var(--panel) 70%,transparent);
    backdrop-filter:blur(8px); padding:20px 14px; position:sticky; top:0; align-self:start;
    height:100vh; overflow-y:auto;
  }
  .brand{ font-family:var(--mono); font-weight:600; font-size:15px; letter-spacing:.02em;
    display:flex; align-items:center; gap:8px; margin:2px 6px 18px; }
  .brand b{ color:var(--accent); }
  .brand .dot{ width:9px; height:9px; border-radius:50%; background:var(--accent);
    box-shadow:0 0 0 3px var(--accent-soft); }
  .navlbl{ font-family:var(--mono); font-size:11px; text-transform:uppercase;
    letter-spacing:.14em; color:var(--dim); margin:14px 8px 8px; }
  .dom{ display:flex; align-items:center; gap:9px; width:100%; text-align:left;
    background:none; border:0; color:var(--mut); font-family:var(--sans); font-size:13.5px;
    padding:7px 9px; border-radius:9px; cursor:pointer; transition:.15s; }
  .dom:hover{ background:var(--card); color:var(--fg); }
  .dom.on{ background:var(--accent-soft); color:var(--fg); }
  .dom .swatch{ width:8px; height:8px; border-radius:2px; flex:none; }
  .dom .n{ flex:1; }
  .dom .c{ font-family:var(--mono); font-size:11px; color:var(--dim); }

  /* main */
  main{ min-width:0; }
  header{ position:sticky; top:0; z-index:9; padding:18px 26px 14px;
    background:linear-gradient(var(--bg) 70%, transparent); }
  .h-top{ display:flex; align-items:baseline; gap:12px; flex-wrap:wrap; margin-bottom:14px; }
  h1{ margin:0; font-size:22px; letter-spacing:-.01em; }
  h1 .thin{ color:var(--mut); font-weight:400; }
  .count{ font-family:var(--mono); font-size:12px; color:var(--accent);
    border:1px solid var(--line); padding:3px 9px; border-radius:20px; }
  .searchbar{ display:flex; align-items:center; gap:10px; background:var(--card);
    border:1px solid var(--line); border-radius:12px; padding:0 12px; height:46px;
    transition:.2s; }
  .searchbar:focus-within{ border-color:var(--accent); box-shadow:0 0 0 4px var(--accent-soft); }
  .searchbar svg{ width:17px; height:17px; color:var(--mut); flex:none; }
  #q{ flex:1; background:none; border:0; outline:0; color:var(--fg);
    font-family:var(--sans); font-size:15px; }
  .kbd{ font-family:var(--mono); font-size:11px; color:var(--dim);
    border:1px solid var(--line); border-radius:6px; padding:2px 6px; }
  .chips{ display:flex; gap:7px; flex-wrap:wrap; margin-top:12px; align-items:center; }
  .chip{ font-family:var(--mono); font-size:12px; color:var(--mut); background:var(--card);
    border:1px solid var(--line); border-radius:20px; padding:5px 11px; cursor:pointer; transition:.15s; }
  .chip:hover{ color:var(--fg); }
  .chip.on{ background:var(--fg); color:var(--bg); border-color:var(--fg); }
  select#sort{ margin-left:auto; font-family:var(--mono); font-size:12px; color:var(--mut);
    background:var(--card); border:1px solid var(--line); border-radius:20px; padding:5px 10px; cursor:pointer; }

  /* grid */
  .grid{ display:grid; grid-template-columns:repeat(auto-fill,minmax(310px,1fr));
    gap:14px; padding:8px 26px 40px; }
  .card{ position:relative; background:var(--card); border:1px solid var(--line);
    border-radius:var(--radius); padding:16px 16px 14px; overflow:hidden;
    animation:rise .5s cubic-bezier(.2,.7,.2,1) both; animation-delay:calc(var(--i,0) * 22ms); }
  .card::before{ content:""; position:absolute; left:0; top:0; bottom:0; width:3px;
    background:var(--dc,var(--accent)); opacity:.9; }
  .card:hover{ border-color:color-mix(in srgb,var(--dc,var(--accent)) 50%,var(--line));
    background:var(--card2); }
  @keyframes rise{ from{ opacity:0; transform:translateY(8px); } to{ opacity:1; transform:none; } }
  .c-head{ display:flex; align-items:center; gap:8px; margin-bottom:3px; }
  .c-name{ font-family:var(--mono); font-weight:600; font-size:15.5px; word-break:break-word; }
  .type{ font-family:var(--mono); font-size:10.5px; letter-spacing:.03em; padding:2px 7px;
    border-radius:6px; border:1px solid var(--line); color:var(--mut); flex:none; }
  .c-meta{ font-family:var(--mono); font-size:11.5px; color:var(--dim); margin-bottom:9px;
    display:flex; gap:8px; flex-wrap:wrap; align-items:center; }
  .c-meta .swatch{ width:7px; height:7px; border-radius:2px; }
  .c-sum{ margin:0 0 9px; font-size:13.5px; color:var(--fg); }
  .c-wtu{ font-size:12.5px; color:var(--mut); border-left:2px solid var(--line);
    padding-left:9px; margin:0 0 10px; }
  .c-wtu b{ color:var(--dim); font-weight:600; font-family:var(--mono); font-size:10px;
    text-transform:uppercase; letter-spacing:.1em; display:block; margin-bottom:1px; }
  .src{ font-family:var(--mono); font-size:11.5px; color:var(--dim);
    display:inline-flex; align-items:center; gap:4px; }
  .src:hover{ color:var(--accent); }
  .tierdot{ width:6px; height:6px; border-radius:50%; display:inline-block; }
  .empty{ grid-column:1/-1; text-align:center; padding:60px 20px; color:var(--mut);
    font-family:var(--mono); }

  @media (max-width:820px){
    .wrap{ grid-template-columns:1fr; }
    aside{ position:static; height:auto; display:none; }
    .grid{ padding:8px 16px 40px; }
    header{ padding:16px; }
  }
</style>
</head>
<body>
<div class="wrap">
  <aside>
    <div class="brand"><span class="dot"></span><span><b>aim</b> · catalog</span></div>
    <div class="navlbl">domains</div>
    <nav id="doms"></nav>
  </aside>
  <main>
    <header>
      <div class="h-top">
        <h1>Capability <span class="thin">Catalog</span></h1>
        <span class="count" id="count"></span>
      </div>
      <div class="searchbar">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="11" cy="11" r="7"/><path d="m21 21-4.3-4.3"/></svg>
        <input id="q" placeholder="ค้นหา capability… ชื่อ / คำอธิบาย / when_to_use" autofocus>
        <span class="kbd">/</span>
      </div>
      <div class="chips" id="types">
        <span class="chip on" data-t="">ทั้งหมด</span>
        <span class="chip" data-t="skill">📄 skill</span>
        <span class="chip" data-t="mcp-tool">🛠️ tool</span>
        <span class="chip" data-t="agent">🤖 agent</span>
        <span class="chip" data-t="rag">📚 rag</span>
        <select id="sort">
          <option value="name">↕ ชื่อ</option>
          <option value="stars">↕ ดาว</option>
          <option value="domain">↕ domain</option>
        </select>
      </div>
    </header>
    <div class="grid" id="grid"></div>
  </main>
</div>
<script>
const DATA = __DATA__;
const TYPE = {skill:"📄 skill","mcp-tool":"🛠️ tool",agent:"🤖 agent",rag:"📚 rag"};
const DC = {dev:"#4c8dff",video:"#ff5c8a",marketing:"#ffab40",business:"#35c48f",
  design:"#b07cff","ai-data":"#22d3ee",maker:"#f97316",finance:"#10b981",
  security:"#ef4444",productivity:"#a3e635"};
const TIER = {"must-have":"#35c48f","nice-to-have":"#ffab40","niche":"#5a6273"};
const $ = s => document.querySelector(s);
let state = {q:"",dom:"",type:"",sort:"name"};

// build domain rail
const counts = {};
DATA.forEach(d => counts[d.domain] = (counts[d.domain]||0)+1);
const doms = Object.keys(counts).sort();
$("#doms").innerHTML =
  `<button class="dom on" data-d=""><span class="swatch" style="background:var(--accent)"></span><span class="n">ทั้งหมด</span><span class="c">${DATA.length}</span></button>` +
  doms.map(d=>`<button class="dom" data-d="${d}"><span class="swatch" style="background:${DC[d]||'#888'}"></span><span class="n">${d}</span><span class="c">${counts[d]}</span></button>`).join("");

function esc(s){ return (s||"").replace(/[&<>"]/g,c=>({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;"}[c])); }

function render(){
  const {q,dom,type,sort} = state;
  let rows = DATA.filter(d=>{
    if(dom && d.domain!==dom) return false;
    if(type && (d.type||"skill")!==type) return false;
    if(q){ const h=(d.name+" "+(d.summary_th||"")+" "+(d.when_to_use||"")+" "+(d.subcategory||"")).toLowerCase();
      if(!h.includes(q)) return false; }
    return true;
  });
  rows.sort((a,b)=> sort==="stars" ? (b.stars||0)-(a.stars||0)
    : sort==="domain" ? (a.domain||"").localeCompare(b.domain||"")||a.name.localeCompare(b.name)
    : a.name.localeCompare(b.name));
  $("#count").textContent = rows.length===DATA.length ? `${DATA.length} รายการ` : `${rows.length} / ${DATA.length}`;
  $("#grid").innerHTML = rows.length ? rows.map((d,i)=>{
    const dc = DC[d.domain]||"var(--accent)";
    const wtu = d.when_to_use && d.when_to_use!==d.summary_th
      ? `<p class="c-wtu"><b>เมื่อไร</b>${esc(d.when_to_use)}</p>` : "";
    const src = d.url ? `<a class="src" href="${esc(d.url)}" target="_blank" rel="noopener">source ↗</a>` : "";
    const stars = d.stars ? `<span>★ ${d.stars}</span>` : "";
    return `<article class="card" style="--i:${Math.min(i,40)};--dc:${dc}">
      <div class="c-head"><span class="c-name">${esc(d.name)}</span>
        <span class="type">${TYPE[d.type]||d.type||"skill"}</span></div>
      <div class="c-meta"><span class="swatch" style="background:${dc}"></span>
        <span>${esc(d.domain)}${d.subcategory?" / "+esc(d.subcategory):""}</span>
        <span class="tierdot" style="background:${TIER[d.tier]||'#5a6273'}"></span><span>${esc(d.tier||"")}</span>
        ${stars}</div>
      <p class="c-sum">${esc(d.summary_th||"")}</p>
      ${wtu}${src}
    </article>`;
  }).join("") : `<div class="empty">// ไม่พบ capability ที่ตรงเงื่อนไข</div>`;
}

// events
$("#q").addEventListener("input",e=>{ state.q=e.target.value.trim().toLowerCase(); render(); });
$("#doms").addEventListener("click",e=>{ const b=e.target.closest(".dom"); if(!b)return;
  document.querySelectorAll(".dom").forEach(x=>x.classList.remove("on")); b.classList.add("on");
  state.dom=b.dataset.d; render(); });
$("#types").addEventListener("click",e=>{ const c=e.target.closest(".chip"); if(!c)return;
  document.querySelectorAll(".chip").forEach(x=>x.classList.remove("on")); c.classList.add("on");
  state.type=c.dataset.t; render(); });
$("#sort").addEventListener("change",e=>{ state.sort=e.target.value; render(); });
document.addEventListener("keydown",e=>{ if(e.key==="/"&&document.activeElement!==$("#q")){ e.preventDefault(); $("#q").focus(); }});
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
    keep = ("name", "type", "domain", "subcategory", "summary_th",
            "when_to_use", "url", "stars", "tier")
    slim = [{k: c.get(k) for k in keep} for c in caps]
    html = _HTML.replace("__DATA__", json.dumps(slim, ensure_ascii=False))
    OUT_PATH.write_text(html, encoding="utf-8")
    print(f"[aim] เขียนหน้าเว็บ -> {OUT_PATH}  ({len(caps)} capability)")
    print(f"[aim] เปิดดู: start {OUT_PATH}")
    return 0
