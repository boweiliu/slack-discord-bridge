"""Merge the sorting workers' reports into the plan and pick the backfill set
(A-071: the latest 50 help-and-bugs, 20 general, 20 show-and-tell threads).

    python3 data/xpost-bridge/backfill/tools/merge_sorting.py <plan.json> <reports-dir> --out <selected-plan.json>

Reads every `chunk-*.md` in <reports-dir> (a worker report with one fenced
json array), fills channel/title/reason/confidence on the plan's threads,
writes the fully sorted plan next to the input (<plan>.sorted.json), and
writes the selected plan: the newest N threads per channel keep their
channel, every other thread is set to "skip" (so `backfill.ts apply` copies
only the selection). Prints the counts and the oldest selected thread per
channel.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from collections import Counter
from pathlib import Path

QUOTA = {"help-and-bugs": 50, "general": 20, "show-and-tell": 20}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("plan")
    ap.add_argument("reports_dir")
    ap.add_argument("--out", required=True)
    ap.add_argument("--quota", default="", help="override, e.g. general=50,help-and-bugs=50,show-and-tell=20")
    args = ap.parse_args()
    for part in args.quota.split(","):
        if "=" in part:
            k, v = part.split("=")
            QUOTA[k.strip()] = int(v)
    plan = json.loads(Path(args.plan).read_text())
    by_ts = {t["rootTs"]: t for t in plan["threads"]}
    seen: Counter[str] = Counter()
    for report in sorted(Path(args.reports_dir).glob("chunk-*.md")):
        m = re.search(r"```json\s*(\[.*?\])\s*```", report.read_text(), re.S)
        if not m:
            print(f"{report}: no json block", file=sys.stderr)
            continue
        for e in json.loads(m.group(1)):
            t = by_ts.get(e.get("rootTs"))
            if t is None:
                print(f"{report}: unknown rootTs {e.get('rootTs')}", file=sys.stderr)
                continue
            if e.get("channel") not in ("help-and-bugs", "general", "show-and-tell", "skip"):
                print(f"{report}: bad channel {e.get('channel')!r} for {e.get('rootTs')}", file=sys.stderr)
                continue
            t["channel"] = e["channel"]
            t["title"] = (e.get("title") or "")[:100] or None
            t["reason"] = (e.get("reason") or "")[:200] or None
            t["confidence"] = e.get("confidence") if e.get("confidence") in ("high", "medium", "low") else "medium"
            seen[e["channel"]] += 1
    sorted_path = Path(args.plan).with_suffix(".sorted.json")
    sorted_path.write_text(json.dumps(plan, indent=2))
    unsorted = sum(1 for t in plan["threads"] if t.get("channel") is None)
    print(f"sorted {sum(seen.values())} threads: {dict(seen)}; unsorted {unsorted}; wrote {sorted_path}")

    threads = sorted(plan["threads"], key=lambda t: float(t["rootTs"]), reverse=True)
    taken: Counter[str] = Counter()
    selected = []
    oldest: dict[str, str] = {}
    for t in threads:
        ch = t.get("channel")
        if ch in QUOTA and taken[ch] < QUOTA[ch]:
            taken[ch] += 1
            oldest[ch] = t["postedAt"]
            selected.append(dict(t))
        else:
            s = dict(t)
            if ch in QUOTA:
                s["reason"] = f"beyond the latest {QUOTA[ch]} for {ch}; " + (s.get("reason") or "")
            s["channel"] = "skip"
            selected.append(s)
    out = dict(plan)
    # The copy posts in this order: oldest first, so the channels read in time order (BACKFILL.md step 5).
    out["threads"] = sorted(selected, key=lambda t: float(t["rootTs"]))
    Path(args.out).write_text(json.dumps(out, indent=2))
    short = {ch: taken[ch] for ch in QUOTA}
    print(f"selected {short} of quota {QUOTA}; oldest selected per channel: {oldest}; wrote {args.out}")
    missing = {ch: QUOTA[ch] - taken[ch] for ch in QUOTA if taken[ch] < QUOTA[ch]}
    if missing:
        print(f"SHORT by {missing}: sort more (older) chunks", file=sys.stderr)
        return 3
    return 0


if __name__ == "__main__":
    sys.exit(main())
