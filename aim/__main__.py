"""Aim CLI — `python -m aim <command>`.

M0: `ping` — เช็กว่าต่อ Qdrant ได้ + list collections (stdlib ล้วน ไม่ต้องลง dep).
"""
from __future__ import annotations

import argparse
import json
import sys
import urllib.error
import urllib.request

from .config import load_settings

# Windows console เป็น cp1252 พิมพ์ emoji/ไทยไม่ได้ — บังคับ utf-8
for _stream in (sys.stdout, sys.stderr):
    try:
        _stream.reconfigure(encoding="utf-8")
    except (AttributeError, ValueError):
        pass


def _get_json(url: str, timeout: float = 10.0) -> dict:
    with urllib.request.urlopen(url, timeout=timeout) as resp:
        return json.loads(resp.read().decode())


def cmd_ping(settings: dict) -> int:
    base = settings["qdrant_url"].rstrip("/")
    url = f"{base}/collections"
    try:
        data = _get_json(url)
    except (urllib.error.URLError, OSError, ValueError) as exc:
        print(f"[aim] ping FAILED -> {url}")
        print(f"      {exc}")
        print("      (Aim ต้องรันใน docker network 'backend' ถึงจะเห็น http://qdrant:6333)")
        return 1

    cols = [c.get("name") for c in data.get("result", {}).get("collections", [])]
    target = settings["collection"]
    print(f"[aim] qdrant OK @ {settings['qdrant_url']}")
    print(f"[aim] collections ({len(cols)}): {', '.join(cols) or '(none)'}")
    state = "EXISTS" if target in cols else "ยังไม่มี (จะสร้างตอน index)"
    print(f"[aim] target collection '{target}': {state}")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="aim", description="Aim — capability router")
    sub = parser.add_subparsers(dest="cmd")
    sub.add_parser("ping", help="เช็กการต่อ Qdrant + list collections")
    p_index = sub.add_parser("index", help="embed catalog เข้า Qdrant (หรือ --local)")
    p_index.add_argument("--local", action="store_true", help="สร้าง local index ในเครื่อง (ไม่ใช้ Qdrant)")
    p_route = sub.add_parser("route", help="บอกงาน -> แนะนำ capability ที่ใช่")
    p_route.add_argument("task", help="คำอธิบายงานเป็นภาษาคน")
    p_route.add_argument("--top-k", type=int, default=5)
    p_route.add_argument("--harness", choices=["claude", "ollama", "both"], default=None)
    p_route.add_argument("--llm", action="store_true", help="LLM re-rank (ต้องมี OPENROUTER_API_KEY)")
    p_route.add_argument("--verify", action="store_true", help="verify คำแนะนำ (กรอง+confidence+gap, implies --llm)")
    p_route.add_argument("--local", action="store_true", help="ค้นในเครื่อง ไม่ต้องใช้ server/Qdrant")
    p_route.add_argument("--json", action="store_true", help="ผลเป็น JSON (ให้ AI/สคริปต์อ่านต่อ)")
    sub.add_parser("web", help="gen หน้าเว็บ browse catalog -> docs/catalog.html")
    p_disc = sub.add_parser("discover", help="หา skill ใหม่มา update catalog (เกณฑ์: คุณภาพ+ความใหม่)")
    p_disc.add_argument("--limit", type=int, default=8, help="จำนวน candidate สูงสุดที่เสนอ")
    p_disc.add_argument("--merge", action="store_true", help="รวม candidate ที่เสนอไว้เข้า catalog")
    p_do = sub.add_parser("do", help="ครบวงจร: route -> โหลด skill -> ลงมือทำ -> คืนผลงาน")
    p_do.add_argument("task", help="คำอธิบายงานเป็นภาษาคน")
    p_do.add_argument("--server", action="store_true", help="ใช้ Qdrant แทน local index")
    p_eval = sub.add_parser("eval", help="วัดคุณภาพ router ด้วย eval set (hit@k + MRR)")
    p_eval.add_argument("--top-k", type=int, default=5)
    p_eval.add_argument("--llm", action="store_true", help="วัดผลหลัง LLM re-rank ด้วย")
    p_eval.add_argument("--server", action="store_true", help="ใช้ Qdrant แทน local index")
    p_eval.add_argument("-v", "--verbose", action="store_true", help="แสดงผลรายเคส")

    args = parser.parse_args(argv)
    settings = load_settings()

    if args.cmd == "ping":
        return cmd_ping(settings)
    if args.cmd == "index":
        if args.local:
            from .local_store import build_local_index
            return build_local_index(settings)
        from .index import cmd_index
        return cmd_index(settings)
    if args.cmd == "route":
        from .router import cmd_route
        backend = "local" if args.local else "qdrant"
        return cmd_route(settings, args.task, args.top_k, args.harness,
                         args.llm, args.verify, backend, args.json)
    if args.cmd == "web":
        from .webgen import cmd_web
        return cmd_web(settings)
    if args.cmd == "discover":
        from .discover import cmd_discover
        return cmd_discover(settings, args.limit, args.merge)
    if args.cmd == "do":
        from .do import cmd_do
        backend = "qdrant" if args.server else "local"
        return cmd_do(settings, args.task, backend)
    if args.cmd == "eval":
        from .eval import cmd_eval
        backend = "qdrant" if args.server else "local"
        return cmd_eval(settings, args.top_k, args.llm, backend, args.verbose)

    parser.print_help()
    return 0


if __name__ == "__main__":
    sys.exit(main())
