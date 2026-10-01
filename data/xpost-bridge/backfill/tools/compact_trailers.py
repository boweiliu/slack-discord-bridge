"""Rewrite the bridge's existing Discord copies from the old several-line
form (one `-# ` line per bridge note, the tag last) to the one trailer line
of D-30: `-# [from Slack](<url>) · ... · xp ...`. Only messages posted by
the bridge's own webhooks and ending in a tag line are touched; the body
(the person's words) is left exactly as it is.

    python3 compact_trailers.py --forum <id> --channels <id>,<id> [--apply]

Needs DISCORD_BOT_TOKEN (run under with_secrets.py). Webhook messages can
only be edited through the webhook that posted them, so the script reads
each channel's webhooks (bot-owned ones carry their token) and edits with
`?thread_id=` for messages inside threads. Rate limits are waited out.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request

API = "https://discord.com/api/v10"
H = {"Authorization": "Bot " + os.environ["DISCORD_BOT_TOKEN"], "User-Agent": "DiscordBot (https://github.com/imbue-ai/xpost-bridge, 0.1)"}
TAG_LINE = re.compile(r"^-# xp [0-9a-f]{10} [0-9a-z]{4}\.[0-9a-z]{4} [0-9a-z]{6,7}(?:\.\d+/\d+)?$")
FROM_SLACK = re.compile(r"^-# from Slack: <(https?://[^>]+)>$")
ATTACHED = re.compile(r"^-# attachment: (.+) \([0-9.]+(?:B|KB|MB|GB)\)$")


def call(method: str, path: str, body: dict | None = None):
    data = json.dumps(body).encode() if body is not None else None
    headers = dict(H)
    if data is not None:
        headers["Content-Type"] = "application/json"
    tries = 0
    while True:
        req = urllib.request.Request(API + path, data=data, headers=headers, method=method)
        try:
            with urllib.request.urlopen(req) as r:
                b = r.read()
                return json.loads(b) if b else None
        except urllib.error.HTTPError as e:
            if e.code == 429:
                time.sleep(float(e.headers.get("Retry-After", "2")))
                continue
            if e.code == 404:
                return None
            if e.code >= 500 and tries < 5:
                tries += 1
                time.sleep(2 * tries)
                continue
            raise RuntimeError(f"{method} {path}: {e.code} {e.read()[:200]!r}") from None


TAG_TOKEN = re.compile(r"^xp [0-9a-f]{10} [0-9a-z]{4}\.[0-9a-z]{4} [0-9a-z]{6,7}(?:\.\d+/\d+)?$")


def normal(name: str) -> str:
    """Discord stores filenames with spaces as underscores."""
    return name.replace(" ", "_")


def compact(content: str, attachment_names: set[str]) -> str | None:
    """The new content, or None when nothing changes."""
    lines = content.split("\n")
    if not lines:
        return None
    last = lines[-1]
    if last.startswith("-# ") and " · " in last and TAG_TOKEN.match(last[3:].split(" · ")[-1]):
        # Already one line: re-split it so attached-file segments can still go.
        segs = last[3:].split(" · ")
        lines = lines[:-1] + ["-# " + s for s in segs]
        if len(lines) >= 2 and not lines[-2].startswith("-# "):
            pass
        content_was_one_line = True
    else:
        content_was_one_line = False
    if not TAG_LINE.match(lines[-1]):
        return None
    # Bridge lines are the trailing run of `-# ` lines (file lines, notes, the tag) and a leading lead line.
    body_end = len(lines) - 1
    while body_end > 0 and lines[body_end - 1].startswith("-# "):
        body_end -= 1
    trailing = lines[body_end:-1]
    lead = []
    body = lines[:body_end]
    if body and body[0].startswith("-# "):
        lead = [body[0][3:]]
        body = body[1:]
    if len(trailing) == 0 and not lead and not content_was_one_line:
        return None  # a bare tag line: already as short as it gets
    segments = list(lead)
    for line in trailing:
        m = FROM_SLACK.match(line)
        if m:
            segments.append(f"[from Slack](<{m.group(1)}>)")
            continue
        a = ATTACHED.match(line)
        if a and (a.group(1) in attachment_names or normal(a.group(1)) in {normal(n) for n in attachment_names}):
            continue  # the attachment is the evidence
        segments.append(line[3:])
    segments.append(lines[-1][3:])
    trailer = "-# " + " · ".join(segments)
    new = ("\n".join(body) + "\n" + trailer) if body else trailer
    return None if new == content else new


def webhooks_for(channel_id: str, cache: dict) -> dict[str, dict]:
    if channel_id not in cache:
        cache[channel_id] = {w["id"]: w for w in (call("GET", f"/channels/{channel_id}/webhooks") or []) if w.get("token")}
    return cache[channel_id]


def all_messages(channel_id: str):
    before = None
    while True:
        q = f"?limit=100" + (f"&before={before}" if before else "")
        page = call("GET", f"/channels/{channel_id}/messages{q}") or []
        if not page:
            return
        for m in page:
            yield m
        before = page[-1]["id"]
        if len(page) < 100:
            return


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--guild", default="1391837726583820409")
    ap.add_argument("--forum", required=True)
    ap.add_argument("--channels", required=True)
    ap.add_argument("--apply", action="store_true")
    args = ap.parse_args()
    hooks: dict = {}
    places: list[tuple[str, str | None]] = []  # (channel to read, parent channel for the webhook / thread id)
    for ch in args.channels.split(","):
        places.append((ch, None))
        for m in all_messages(ch):
            if m.get("thread"):
                places.append((m["thread"]["id"], ch))
    active = call("GET", f"/guilds/{args.guild}/threads/active")["threads"]
    for t in active:
        if t.get("parent_id") == args.forum:
            places.append((t["id"], args.forum))
    changed = skipped = failed = 0
    for read_id, parent in places:
        for m in all_messages(read_id):
            if not m.get("webhook_id"):
                continue
            new = compact(m.get("content") or "", {a["filename"] for a in m.get("attachments", [])})
            if new is None:
                skipped += 1
                continue
            hook = webhooks_for(parent or read_id, hooks).get(m["webhook_id"])
            if hook is None:
                print(f"no webhook token for {m['webhook_id']} in {parent or read_id}; message {m['id']} left", file=sys.stderr)
                failed += 1
                continue
            if args.apply:
                thread_q = f"?thread_id={read_id}" if parent else ""
                call("PATCH", f"/webhooks/{hook['id']}/{hook['token']}/messages/{m['id']}{thread_q}", {"content": new, "allowed_mentions": {"parse": []}})
                time.sleep(0.4)
            changed += 1
    print(f"{'rewrote' if args.apply else 'would rewrite'} {changed} copies; {skipped} already compact or not copies; {failed} without a webhook token", file=sys.stderr)
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
