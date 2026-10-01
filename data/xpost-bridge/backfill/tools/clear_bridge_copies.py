"""List (and with --delete, remove) every bridge copy in the given Discord
channels: forum posts whose starter carries the `-# xp ...` tag line, and
tagged bot/webhook messages in text channels (with the thread on them).
Only tagged automated messages are touched; nothing a person wrote.

    python3 clear_bridge_copies.py --forum <id> --channels <id>,<id> [--delete]

Needs DISCORD_BOT_TOKEN in the environment (run under with_secrets.py).
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import time
import urllib.error
import urllib.request

API = "https://discord.com/api/v10"
TAG = re.compile(r"(?m)^-# xp [0-9a-f]{10} ")
H = {"Authorization": "Bot " + os.environ["DISCORD_BOT_TOKEN"], "User-Agent": "DiscordBot (https://github.com/imbue-ai/xpost-bridge, 0.1)"}


def call(method: str, path: str):
    while True:
        req = urllib.request.Request(API + path, headers=H, method=method)
        try:
            with urllib.request.urlopen(req) as r:
                body = r.read()
                return json.loads(body) if body else None
        except urllib.error.HTTPError as e:
            if e.code == 429:
                time.sleep(float(e.headers.get("Retry-After", "2")))
                continue
            if e.code == 404:
                return None
            raise


def is_copy(m: dict) -> bool:
    return bool(m and (m["author"].get("bot") or m.get("webhook_id")) and TAG.search(m.get("content", "") or ""))


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--guild", default="1391837726583820409")
    ap.add_argument("--forum", required=True)
    ap.add_argument("--channels", required=True)
    ap.add_argument("--delete", action="store_true")
    args = ap.parse_args()
    victims: list[tuple[str, str, str]] = []  # (kind, id, label)

    threads = [t for t in call("GET", f"/guilds/{args.guild}/threads/active")["threads"] if t.get("parent_id") == args.forum]
    archived = call("GET", f"/channels/{args.forum}/threads/archived/public?limit=100") or {"threads": []}
    threads += [t for t in archived["threads"] if t.get("parent_id") == args.forum]
    for t in threads:
        starter = call("GET", f"/channels/{t['id']}/messages/{t['id']}")
        if is_copy(starter):
            victims.append(("thread", t["id"], f"forum post '{t['name'][:60]}'"))
    for ch in args.channels.split(","):
        msgs = call("GET", f"/channels/{ch}/messages?limit=100") or []
        for m in msgs:
            if is_copy(m):
                victims.append(("message", f"{ch}/{m['id']}", f"message '{(m.get('content') or '')[:60]!r}'"))
                if m.get("thread"):
                    victims.append(("thread", m["thread"]["id"], f"thread on it '{m['thread'].get('name', '')[:40]}'"))
    for kind, ident, label in victims:
        print(("DELETE " if args.delete else "would delete ") + kind + " " + ident + ": " + label)
        if args.delete:
            if kind == "thread":
                call("DELETE", f"/channels/{ident}")
            else:
                ch, mid = ident.split("/")
                call("DELETE", f"/channels/{ch}/messages/{mid}")
            time.sleep(0.5)
    print(f"{len(victims)} items", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
