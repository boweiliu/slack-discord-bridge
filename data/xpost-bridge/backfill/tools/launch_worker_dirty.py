"""Launch one background worker the way launch-task's `launch` does, but without
its clean-working-tree gate (another chat keeps this shared checkout dirty).
The worker is still created from the committed HEAD; nothing uncommitted
reaches it. Same stamping, sync and first message as the launcher, so `await`,
`report`, `reply` and `destroy` work unchanged.

    python3 launch_worker_dirty.py --name xpost-sort-3 --template worker-pi \
        --runtime-dir data/.tasks/launch-task/xpost-sort-3/ --task-file data/.tasks/launch-task/xpost-sort-3/task.md
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path


def set_field(text: str, key: str, value: str) -> str:
    assert text.startswith("---\n"), "task file needs YAML frontmatter"
    end = text.index("\n---", 4)
    head, body = text[4:end], text[end:]
    lines = [l for l in head.split("\n") if not l.startswith(f"{key}:")]
    lines.append(f"{key}: {value}")
    return "---\n" + "\n".join(lines) + body


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--name", required=True)
    ap.add_argument("--template", required=True)
    ap.add_argument("--runtime-dir", required=True)
    ap.add_argument("--task-file", required=True)
    args = ap.parse_args()
    top = Path(subprocess.run(["git", "rev-parse", "--show-toplevel"], check=True, capture_output=True, text=True).stdout.strip())
    task = Path(args.task_file).resolve()
    rel_task = task.relative_to(top).as_posix()
    rel_runtime = Path(args.runtime_dir).resolve().relative_to(top).as_posix().rstrip("/") + "/"
    lead_id = os.environ.get("MNGR_AGENT_ID", "")
    lead_work_dir = os.environ.get("MNGR_AGENT_WORK_DIR", str(top))
    text = task.read_text()
    text = set_field(text, "task_file", rel_task)
    if lead_id:
        text = set_field(text, "lead_agent", lead_id)
    text = set_field(text, "lead_work_dir", lead_work_dir)
    task.write_text(text)

    argv = ["mngr", "create", args.name, "-t", args.template, "--label", "agent_created=true", "--format", "jsonl"]
    if lead_id:
        argv += ["--label", f"lead_agent={lead_id}"]
    argv += ["--label", f"runtime_dir={rel_runtime}"]
    created = subprocess.run(argv, check=True, stdout=subprocess.PIPE, text=True)
    agent_id = None
    for line in created.stdout.splitlines():
        try:
            ev = json.loads(line)
        except ValueError:
            continue
        if isinstance(ev, dict) and ev.get("event") == "created" and ev.get("agent_id"):
            agent_id = ev["agent_id"]
    if agent_id:
        task.write_text(set_field(task.read_text(), "worker_agent_id", agent_id))
    subprocess.run(["mngr", "rsync", str(top / rel_runtime), f"{args.name}:{rel_runtime}", "--uncommitted-changes=clobber"], check=True)
    if agent_id:
        subprocess.run([sys.executable, str(top / "system/scripts/message_chat.py"), agent_id, "--message-file", str(task)], check=True)
    else:
        subprocess.run(["mngr", "message", args.name, "--message-file", str(task)], check=True)
    print(f"launched {args.name} (agent id {agent_id})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
