"""discover — ให้ Aim หา capability ใหม่มา update ตัวเอง.

หลักการ (ตามที่ตั้งใจ): ตัดสินที่ "คุณภาพจริง + ความใหม่" ไม่ใช่ดาว/ยอดนิยม
1. ค้น GitHub หา skill repo ที่ "เพิ่งอัปเดตล่าสุด" (sort=updated)
2. กรองตัวที่มีใน catalog แล้วทิ้ง
3. ดึง SKILL.md ให้ LLM ตัดสินคุณภาพ+ประโยชน์ -> เสนอ catalog entry
4. จัดอันดับด้วย freshness + quality (ดาวน้ำหนักน้อยมาก)
5. เขียนคิวลง data/discovered.json -> --merge ค่อยรวมเข้า catalog

ออกแบบให้เป็น "คิวรอรีวิว" ไม่ auto-merge มั่ว (Aim = ที่ปรึกษา ไม่ใช่ทำเอง).
"""
from __future__ import annotations

import json
import math
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

from .index import DATA_PATH, _embed_text  # noqa: F401  (_embed_text re-export for callers)
from .llm import _chat, _strip_fences

DISCOVERED_PATH = DATA_PATH.parent / "discovered.json"
_GH_API = "https://api.github.com"


def _gh(url: str, token: str | None) -> dict | list | None:
    headers = {"User-Agent": "aim-discover", "Accept": "application/vnd.github+json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    try:
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req, timeout=30) as resp:
            return json.loads(resp.read().decode())
    except (urllib.error.URLError, OSError, ValueError) as exc:
        print(f"[aim] github โหลดไม่ได้: {url}\n      {exc}")
        return None


def _fetch_raw(full: str, branch: str, path: str, limit: int = 16000) -> str | None:
    url = f"https://raw.githubusercontent.com/{full}/{branch}/{path}"
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "aim-discover"})
        with urllib.request.urlopen(req, timeout=20) as resp:
            return resp.read().decode("utf-8", errors="replace")[:limit]
    except (urllib.error.URLError, OSError, ValueError):
        return None


def _existing_sources(caps: list[dict]) -> set[str]:
    return {c.get("source", "") for c in caps}


def _search_recent_repos(token: str | None, n: int) -> list[dict]:
    """repo ที่เกี่ยวกับ claude skill เรียงตาม 'เพิ่งอัปเดต' (ไม่ใช่ดาว)."""
    q = urllib.parse.quote('claude skill SKILL.md in:name,description,readme')
    url = f"{_GH_API}/search/repositories?q={q}&sort=updated&order=desc&per_page={n}"
    data = _gh(url, token)
    if not isinstance(data, dict):
        return []
    out = []
    for r in data.get("items", []):
        out.append({
            "full": r.get("full_name"),
            "branch": r.get("default_branch", "main"),
            "stars": r.get("stargazers_count", 0),
            "pushed_at": r.get("pushed_at", ""),
            "desc": (r.get("description") or "")[:300],
        })
    return out


def _find_skill_files(full: str, branch: str, token: str | None, cap: int = 3) -> list[str]:
    """หา path ของ SKILL.md ใน repo (สูงสุด cap ตัว) ผ่าน git tree."""
    data = _gh(f"{_GH_API}/repos/{full}/git/trees/{branch}?recursive=1", token)
    if not isinstance(data, dict):
        return []
    paths = [t.get("path") for t in data.get("tree", [])
             if (t.get("path") or "").upper().endswith("SKILL.MD")]
    # ชอบตัวตื้นก่อน (โครงสร้างชัดกว่า)
    paths.sort(key=lambda p: p.count("/"))
    return paths[:cap]


def _freshness(pushed_at: str) -> float:
    """0..1 — อัปเดตใหม่กว่า = สูงกว่า (อ้างอิงครึ่งชีวิต ~180 วัน)."""
    if not pushed_at:
        return 0.0
    try:
        dt = datetime.fromisoformat(pushed_at.replace("Z", "+00:00"))
    except ValueError:
        return 0.0
    days = max(0.0, (datetime.now(timezone.utc) - dt).total_seconds() / 86400)
    return math.exp(-days / 180.0)  # 180 วัน -> ~0.37


def _popularity(stars: int) -> float:
    """0..1 — log scale, อิ่มตัวเร็ว (ดาวเป็นแค่ tiebreak)."""
    return min(1.0, math.log10(max(1, stars) + 1) / 4.0)  # 10k ดาว ~1.0


def _score(quality: float, pushed_at: str, stars: int) -> float:
    """quality นำ, freshness รอง, popularity จิ๊บเดียว — ของใหม่ที่ดีจะลอยขึ้น."""
    return round(0.70 * quality + 0.25 * _freshness(pushed_at) + 0.05 * _popularity(stars), 4)


_JUDGE_SCHEMA = (
    '{"keep":true/false,"quality":0.0-1.0,"domain":"dev|video|marketing|business|'
    'design|ai-data|maker|finance|security|productivity","subcategory":"<สั้น>",'
    '"type":"skill","tier":"must-have|nice-to-have|niche","summary_th":"<1 ประโยค>",'
    '"when_to_use":"<เมื่อไรควรใช้ ภาษาไทย คม>","novelty_th":"<ใหม่/ต่างตรงไหน>"}'
)


def _judge(settings: dict, name: str, doc: str, desc: str) -> dict | None:
    prompt = (
        f"คุณคือบรรณาธิการคลังความสามารถ AI ที่เน้น \"ของใหม่ที่ดีจริง\" ไม่ใช่ของดังอย่างเดียว.\n"
        f"ประเมิน skill นี้จาก \"เนื้อหาจริง\" (ไม่เกี่ยวกับจำนวนดาว):\n\n"
        f"ชื่อ repo/skill: {name}\nคำอธิบาย repo: {desc}\n\n"
        f"=== SKILL.md (ตัดมาบางส่วน) ===\n{doc[:8000]}\n=== จบ ===\n\n"
        f"ตัดสิน: คุณภาพเนื้อหา (ชัด/ใช้ได้จริง/มีขั้นตอน), ความแปลกใหม่/มีประโยชน์, "
        f"เหมาะเข้าคลังไหม. ถ้ากลวง/ซ้ำของพื้นๆ/แค่ README โล่งๆ ให้ keep=false.\n"
        f"ตอบ JSON เท่านั้นตามรูปแบบนี้:\n{_JUDGE_SCHEMA}"
    )
    content = _chat(settings, prompt)
    if content is None:
        return None
    try:
        return json.loads(_strip_fences(content))
    except (ValueError, TypeError):
        return None


def _load_caps() -> list[dict]:
    return json.loads(DATA_PATH.read_text(encoding="utf-8")).get("capabilities", [])


def cmd_discover(settings: dict, limit: int = 8, do_merge: bool = False) -> int:
    if do_merge:
        return _merge(settings)

    if not settings.get("openrouter_key"):
        print("[aim] discover ต้องใช้ LLM ตัดสินคุณภาพ — ตั้ง OPENROUTER_API_KEY / AIM_SECRETS_FILE ก่อน")
        return 1

    token = settings.get("github_token")
    caps = _load_caps()
    have = _existing_sources(caps)
    have_names = {c.get("name") for c in caps}

    print(f"\n🔎 discover — ค้น skill ใหม่ (เกณฑ์: คุณภาพ+ความใหม่, ไม่ใช่ดาว)")
    print(f"   catalog ปัจจุบัน {len(caps)} ตัว · github token: {'มี' if token else 'ไม่มี (rate limit ต่ำ)'}")

    repos = _search_recent_repos(token, max(limit * 3, 20))
    if not repos:
        print("   หา repo ไม่ได้ (rate limit หรือเน็ต) — ลองใส่ GITHUB_TOKEN")
        return 1

    new_repos = [r for r in repos if r["full"] not in have]
    print(f"   เจอ {len(repos)} repo, ใหม่ (ยังไม่มีใน catalog) {len(new_repos)} repo\n")

    proposals: list[dict] = []
    for r in new_repos:
        if len(proposals) >= limit:
            break
        full = r["full"]
        for path in _find_skill_files(full, r["branch"], token):
            name = Path(path).parent.name or full.split("/")[-1]
            if name in have_names or any(p["name"] == name for p in proposals):
                continue
            doc = _fetch_raw(full, r["branch"], path)
            if not doc:
                continue
            verdict = _judge(settings, f"{full}:{name}", doc, r["desc"])
            if not verdict or not verdict.get("keep"):
                print(f"   ✗ ข้าม {full}/{name} ({(verdict or {}).get('novelty_th','คุณภาพไม่ผ่าน')})")
                continue
            q = float(verdict.get("quality", 0.0))
            entry = {
                "domain": verdict.get("domain", "productivity"),
                "name": name,
                "source": full,
                "url": f"https://github.com/{full}/blob/{r['branch']}/{path}",
                "stars": r["stars"],
                "subcategory": verdict.get("subcategory", ""),
                "summary_th": verdict.get("summary_th", ""),
                "relevance": 3,
                "quality": round(q * 5),
                "tier": verdict.get("tier", "nice-to-have"),
                "type": "skill",
                "harness": "claude",
                "when_to_use": verdict.get("when_to_use", verdict.get("summary_th", "")),
                "_score": _score(q, r["pushed_at"], r["stars"]),
                "_pushed_at": r["pushed_at"],
                "_novelty_th": verdict.get("novelty_th", ""),
            }
            proposals.append(entry)
            print(f"   ✓ {name}  [{entry['domain']}]  score={entry['_score']}  ⭐{r['stars']}  ({r['pushed_at'][:10]})")
            if len(proposals) >= limit:
                break

    proposals.sort(key=lambda x: x["_score"], reverse=True)
    DISCOVERED_PATH.write_text(
        json.dumps({"count": len(proposals), "candidates": proposals}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(f"\n   เสนอ {len(proposals)} ตัว -> {DISCOVERED_PATH.name}")
    if proposals:
        print("   ดูแล้วโอเค รวมเข้า catalog ด้วย: python -m aim discover --merge")
    return 0


def _merge(settings: dict) -> int:
    if not DISCOVERED_PATH.exists():
        print(f"[aim] ยังไม่มี {DISCOVERED_PATH.name} — รัน `aim discover` ก่อน")
        return 1
    proposals = json.loads(DISCOVERED_PATH.read_text(encoding="utf-8")).get("candidates", [])
    if not proposals:
        print("[aim] ไม่มี candidate ให้รวม")
        return 0

    catalog = json.loads(DATA_PATH.read_text(encoding="utf-8"))
    caps = catalog.get("capabilities", [])
    have = {(c.get("source"), c.get("name")) for c in caps}

    added = 0
    for p in proposals:
        key = (p.get("source"), p.get("name"))
        if key in have:
            continue
        clean = {k: v for k, v in p.items() if not k.startswith("_")}  # ทิ้ง field discovery
        caps.append(clean)
        have.add(key)
        added += 1

    catalog["capabilities"] = caps
    DATA_PATH.write_text(json.dumps(catalog, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"[aim] รวมเข้า catalog แล้ว +{added} ตัว (รวม {len(caps)})")
    print("[aim] อย่าลืม re-index: python -m aim index --local")
    return 0
