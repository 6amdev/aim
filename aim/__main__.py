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
    sub.add_parser("index", help="embed catalog เข้า Qdrant collection")
    p_route = sub.add_parser("route", help="บอกงาน -> แนะนำ capability ที่ใช่")
    p_route.add_argument("task", help="คำอธิบายงานเป็นภาษาคน")
    p_route.add_argument("--top-k", type=int, default=5)
    p_route.add_argument("--harness", choices=["claude", "ollama", "both"], default=None)

    args = parser.parse_args(argv)
    settings = load_settings()

    if args.cmd == "ping":
        return cmd_ping(settings)
    if args.cmd == "index":
        from .index import cmd_index
        return cmd_index(settings)
    if args.cmd == "route":
        from .router import cmd_route
        return cmd_route(settings, args.task, args.top_k, args.harness)

    parser.print_help()
    return 0


if __name__ == "__main__":
    sys.exit(main())
