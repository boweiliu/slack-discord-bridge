"""Read-only audit: find any origin whose bridge copy exists as a
top-level post in more than one Discord place (a general/show-and-tell
copy from the backfill plus a stray forum copy from the D-29 bug, most
likely). Prints a report; deletes nothing.

    python3 audit_cross_channel_dupes.py --forum <id> --channels <id>,<id>,...

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
# D-30: the tag is the last " · "-joined segment of the final "-# " line.
TAG = re.compile(r"xp ([0-9a-f]{10}) ([0-9a-z]{4}\.[0-9a-z]{4}) ([0-9a-z]{6,7})(?:\.\d+/\d+)?$")
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


def tag_of(m: dict) -> str | None:
    if not (m and (m["author"].get("bot") or m.get("webhook_id"))):
        return None
    lines = (m.get("content") or "").split("\n")
    if not lines or not lines[-1].startswith("-# "):
        return None
    last_segment = lines[-1][3:].split(" · ")[-1]
    found = TAG.match(last_segment)
    return found.group(1) if found else None


def all_text_messages(channel_id: str):
    before = None
    while True:
        q = f"?limit=100" + (f"&before={before}" if before else "")
        page = call("GET", f"/channels/{channel_id}/messages{q}") or []
        if not page:
            return
        yield from page
        before = page[-1]["id"]
        if len(page) < 100:
            return


def all_forum_starters(guild_id: str, forum_id: str):
    threads = [t for t in (call("GET", f"/guilds/{guild_id}/threads/active") or {"threads": []})["threads"] if t.get("parent_id") == forum_id]
    before = None
    while True:
        q = f"?limit=100" + (f"&before={before}" if before else "")
        archived = call("GET", f"/channels/{forum_id}/threads/archived/public{q}") or {"threads": [], "has_more": False}
        page = [t for t in archived["threads"] if t.get("parent_id") == forum_id]
        threads += page
        if not archived.get("has_more") or not page:
            break
        before = page[-1]["thread_metadata"]["archive_timestamp"]
    for t in threads:
        starter = call("GET", f"/channels/{t['id']}/messages/{t['id']}")
        if starter:
            yield t["id"], starter


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--guild", default="1391837726583820409")
    ap.add_argument("--forum", required=True)
    ap.add_argument("--channels", required=True)
    args = ap.parse_args()

    by_hash: dict[str, list[tuple[str, str]]] = {}

    for ch in args.channels.split(","):
        for m in all_text_messages(ch):
            h = tag_of(m)
            if h:
                by_hash.setdefault(h, []).append((f"channel {ch}", m["id"]))

    for thread_id, starter in all_forum_starters(args.guild, args.forum):
        h = tag_of(starter)
        if h:
            by_hash.setdefault(h, []).append((f"forum post {thread_id}", starter["id"]))

    # Any origin with more than one top-level copy is a duplicate, whether
    # the two copies landed in the same channel or different ones.
    dupes = {h: places for h, places in by_hash.items() if len(places) > 1}

    print(f"{len(by_hash)} tagged top-level copies scanned, {len(dupes)} origin hashes with more than one copy", file=sys.stderr)
    for h, places in dupes.items():
        print(f"origin {h}:")
        for place, mid in places:
            print(f"  {place} message/thread {mid}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
