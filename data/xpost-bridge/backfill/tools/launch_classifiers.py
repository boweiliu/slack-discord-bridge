"""Split a backfill plan into chunks and launch one background worker per chunk
to sort the threads (A-071). Run from the workspace root:

    python3 data/xpost-bridge/backfill/tools/launch_classifiers.py <plan.json> --workers 8 [--only 3,4] [--template worker-pi] [--launch]

Without --launch it only writes the task files and chunk files under
data/.tasks/launch-task/xpost-sort-<n>/ and prints the launch commands.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

TASK_BODY = """
# Task: sort {count} Slack threads into Discord channels (chunk {index} of {total})

## What to do

`chunk.json` beside this file (in the same directory as this task file) holds
{count} threads from the bridged Slack channel: for each, the
first message, who posted it, when, and samples of the replies. Read every
thread and decide where it belongs in the Discord:

- `help-and-bugs`: a bug, a bug report, or a complaint: something not working,
  an error, a problem, a request for help with a specific issue.
- `general`: a feature request, a generic question, feedback, an announcement,
  conversation about using the product, anything broad or social.
- `show-and-tell`: a brag, a share, an "I did this": someone showing something
  they made or achieved with the product (a demo, a result, "look what I built").
- `skip`: purely internal or operational chatter with no value to a community
  reader (meeting logistics, "can you DM me", test messages, empty messages).

The unit is the thread: the replies land wherever the first message lands, so
judge the thread as a whole, but by what it is *about*, which the first message
usually settles. When a thread is both (a question that turns out to be a bug),
prefer `help-and-bugs`. When unsure between `general` and `skip`, prefer
`general`.

For `help-and-bugs` threads also write a post title: up to 90 characters, the
problem in the reporter's own words, no trailing period. For the others the
title is an empty string.

Do this yourself, by reading; do not call any external service, do not write
any code or scripts beyond what you need to read and write JSON, and do not
change anything in the repository. Nothing in the chunk leaves this machine.

## Output

Deliver the result as the body of your `done` report: one fenced ```json
block containing a JSON array with exactly one object per thread, in the
chunk's order:

```json
[
  {{"rootTs": "<the thread's rootTs, verbatim>", "channel": "help-and-bugs" | "general" | "show-and-tell" | "skip", "title": "<title or empty string>", "reason": "<one short sentence>", "confidence": "high" | "medium" | "low"}}
]
```

Every `rootTs` from the chunk must appear exactly once. Before delivering,
check that the array parses and has {count} entries.

## Success criteria

- {count} entries, one per thread, every `rootTs` matched, every `channel`
  one of the four values, every `help-and-bugs` entry with a non-empty title
  of at most 90 characters.
- Valid JSON inside the report body.

## Reporting back
Follow `.agents/shared/references/worker-reporting.md` for the full
report procedure: parse this task's frontmatter for `TASK_FILE` /
`LEAD_WORK_DIR` / `FINISH_REPORT_PATH`, then write your report body to a
file and deliver it with the launcher's `report` subcommand, which writes
the report and copies it into the lead's checkout for you:

`create_worker.py report --task-file "$TASK_FILE" --type <gate|status> --name <name> --body-file <body-file>`

Substitutions for this task:

- `<TASK_FILE>` -> the `task_file` path stamped in this file's frontmatter
- Valid `name:` values: `question` (a mid-flight gate, valid at any
  point of any run), `done` / `stuck` (terminal).
- Milestones (`type: milestone`, any name; non-blocking) follow
  `worker-reporting.md`'s "Milestone reports": a file under
  `milestones/` beside `report.md`, delivered the same way; its
  `<RUNTIME_REPORTS_DIR>` is `dirname "$FINISH_REPORT_PATH"`.

For a mid-flight `question` gate, stop your turn after delivering the
report -- the lead's reply arrives as a message in your chat and you
resume. For terminal statuses, the run ends. A milestone is the
exception: it never stops your turn -- deliver it and carry straight on.
"""


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("plan")
    ap.add_argument("--workers", type=int, default=8)
    ap.add_argument("--prefix", default="xpost-sort")
    ap.add_argument("--launch", action="store_true")
    ap.add_argument("--template", default="worker-pi", help="mngr create template (worker-pi: the light pi harness; worker: claude)")
    ap.add_argument("--only", default="", help="comma-separated chunk indexes to write/launch (default all)")
    args = ap.parse_args()
    only = {int(x) for x in args.only.split(",") if x.strip()}
    plan = json.loads(Path(args.plan).read_text())
    threads = sorted(plan["threads"], key=lambda t: float(t["rootTs"]), reverse=True)  # newest first
    n = args.workers
    size = -(-len(threads) // n)
    chunks = [threads[i : i + size] for i in range(0, len(threads), size)]
    print(f"{len(threads)} threads -> {len(chunks)} chunks of up to {size}", file=sys.stderr)
    fields = ("rootTs", "postedAt", "author", "rootText", "replyCount", "fileCount", "replySamples", "permalink")
    for i, chunk in enumerate(chunks, start=1):
        if only and i not in only:
            continue
        name = f"{args.prefix}-{i}"
        run = Path("data/.tasks/launch-task") / name
        run.mkdir(parents=True, exist_ok=True)
        (run / "chunk.json").write_text(json.dumps([{k: t.get(k) for k in fields} for t in chunk], indent=1))
        task = run / "task.md"
        task.write_text(
            "---\n"
            f"finish_report_path: data/.tasks/launch-task/{name}/reports/report.md\n"
            "---\n"
            + TASK_BODY.format(count=len(chunk), index=i, total=len(chunks))
        )
        cmd = [
            "uv", "run", ".agents/skills/launch-task/scripts/create_worker.py", "launch",
            "--name", name, "--template", args.template,
            "--runtime-dir", f"data/.tasks/launch-task/{name}/",
            "--task-file", f"data/.tasks/launch-task/{name}/task.md",
        ]
        print(" ".join(cmd))
        if args.launch:
            subprocess.run(cmd, check=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
