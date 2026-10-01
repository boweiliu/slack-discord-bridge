---
title: "Slack-Discord bridge"
description: "A bidirectional Slack<->Discord message bridge with a monitoring dashboard. This is a pre-classifier v1 snapshot: no live-traffic sorting classifier, manual routing overrides, or hardened cross-channel duplicate-prevention invariant yet -- those are planned follow-ups."
thumbnail: "template.svg"
version: v1
format: v2
---

# Slack-Discord bridge

This file is the manifest for the **Slack-Discord bridge** template (slug:
`slack-discord-bridge`). It is the one document a future agent reads to understand,
present, and adapt this template. If you are an agent in a mind that was
created from this template, this file is your script: read all of it, then
follow "How to adapt it" below.

## What it is

A bidirectional Slack<->Discord message bridge with a monitoring dashboard. This is a pre-classifier v1 snapshot: no live-traffic sorting classifier, manual routing overrides, or hardened cross-channel duplicate-prevention invariant yet -- those are planned follow-ups.

**This is a pre-classifier v1 snapshot.** The bridge copies every message
that crosses the connected channels, both directions, as-is -- it does not
yet sort incoming traffic, offer manual routing overrides, or enforce a
hardened invariant against the same message landing twice across channels.
Those are planned follow-ups for a later version of this template, brought
in through an `update-published-template` run, not something this snapshot
does today.

What it does today: several independent instances of a bridge service each
copy new Slack messages into matching Discord channels and new Discord
messages back into Slack, with reactions, threading, and author identity
carried across (see the bridge engine's own docs for the exact behavior).
Each instance works out for itself what it has already copied -- there is
no shared state between instances. Alongside the bridge, a read-only
dashboard shows what has been copied, when, and whether anything is stuck,
by reading a status file the bridge writes as it runs. A companion set of
one-off scripts (not a running service) helps an operator chunk up and
classify a large Slack history into categories, merge the results, and
clean up or audit the Discord side of a bridge's copies.

## How it works

The snapshot includes these paths (each is a repo-root-relative path copied
from the original mind onto a clean default-workspace-template base):

- `system/apps/xpost_dashboard`
- `system/supervisord.conf.d/xpost-dashboard.conf`
- `system/supervisord.conf.d/xpost-bridge.conf`
- `data/xpost-bridge/backfill/tools` (data, explicitly opted in)

This repo holds only the operator-side pieces. The actual bridge engine --
message delivery, turn-taking, identity, content conversion, all of it --
lives in a separate, deliberately NOT-copied-in repo:
**`github.com/imbue-ai/xpost-bridge`** (private; you need your own access or
your own fork). Clone it yourself, conventionally into
`.external_worktrees/xpost-bridge/` per this template's own `AGENTS.md`
convention for external dependencies under active development, then follow
its own `AGENTS.md` -> `docs/START_HERE.md` -> `docs/SETUP.md` to create your
own Slack app and Discord bot and get credentials -- nothing in this
template talks to either platform for you. `npm install` inside that clone
too, since `xpost-bridge.conf` below runs it with `tsx` via
`node_modules/.bin/tsx`.

- `system/apps/xpost_dashboard/`: a Flask app, a pure read-only observer of
  a running bridge instance's status. It never talks to Slack, Discord, or
  the bridge process directly -- it only reads a JSON snapshot the bridge
  writes to `XPOST_DASHBOARD_DATA_DIR/status.json` on its own cadence (see
  the app's own `README.md` and `status_store.py` for the full schema). `/`
  serves the live page; `/mock` serves a fully populated reference page so
  you can see what a working dashboard looks like before any bridge
  instance has reported.
- `system/supervisord.conf.d/xpost-dashboard.conf`: runs the dashboard as
  the `xpost-dashboard` program, registers its port with
  `forward_port.py`, and serves it on `http://localhost:8082`.
- `system/supervisord.conf.d/xpost-bridge.conf`: an *example* of how to run
  one bridge instance as the `xpost-bridge` program, against the engine
  repo checked out at `.external_worktrees/xpost-bridge`. Every
  Imbue-specific id from the original deployment has been replaced with a
  `REPLACE_WITH_*` placeholder -- see "Requirements" below. It reads its
  Slack and Discord credentials through `with_secrets.py` wrapping the two
  secret files declared there, and it writes its status to the path the
  dashboard reads from, which is how the two programs connect without
  talking to each other directly.
- `data/xpost-bridge/backfill/tools/`: six standalone scripts (not a
  running service) for a one-off migration of a Slack message backlog:
  chunking a backlog into parallel classification workers (via this mind
  platform's own `launch-task` mechanism, which every mind already has),
  merging the workers' verdicts and picking a bounded set per category,
  auditing the Discord side for cross-channel duplicates, clearing a false
  start, and compacting the bridge's own trailer lines on existing copies.
  These only produce or consume local files and Discord API calls; they are
  not wired into the two supervisord programs above.

## Recipe

This template is version `v1`. It is not a fork of the
workspace it came from -- it is DERIVED from it by a recipe: include these
paths, leave these out, apply these published-version rules. An update re-runs
the recipe against the current workspace and publishes the result as the next
version, so anything excluded stays excluded even though it still exists in the
source workspace.

The recipe is machine-read, so it lives in the sibling
[`template.toml`](template.toml) -- its `[recipe]` table -- along with
the structured requirements and the environment this template needs
installed. That file is authoritative for all of it; this one holds the prose.

## Requirements

Everything the adopting mind must deal with before this template is really
theirs. Two kinds of entry, handled at different times:

- **Activation** -- what must be SET UP before anything runs, in the
  machine-readable `requires_` forms below. The adopting agent acts on these
  ITSELF, first, before asking anything.
- **Adaptation** -- what must be DECIDED or REWIRED, in prose. Worked through
  interactively with the user, after activation.

- requires_secret: data/.secrets/discord-xpost.env with DISCORD_BOT_TOKEN (for the companion xpost-bridge service (system/supervisord.conf.d/xpost-bridge.conf), not the dashboard itself -- see the bridge repo's docs/SETUP.md)
- requires_secret: data/.secrets/slack-xpost.env with SLACK_BOT_TOKEN, SLACK_APP_TOKEN (for the companion xpost-bridge service (system/supervisord.conf.d/xpost-bridge.conf), not the dashboard itself -- see the bridge repo's docs/SETUP.md)

No `requires_permission:` lines apply: this bridge uses its own dedicated
Slack app and Discord bot, created directly in each platform's own
developer console per the engine repo's `docs/SETUP.md`, not this
workspace's latchkey Slack/Discord connectors. No `requires_llm:` line
applies either: nothing in the included paths calls an LLM API directly --
the backfill chunking scripts parallelize classification by launching
sub-agents through this mind platform's own `launch-task` mechanism (every
mind already has this), not a separate keyed or keyless Claude integration
of their own. (The *engine* repo's own backfill tooling does call Claude
directly for an alternative classification approach -- that is the engine
repo's own concern, documented in its own docs, not something this
template needs to declare.)

- Clone `github.com/imbue-ai/xpost-bridge` (or your own fork of it) and
  complete its own setup (`AGENTS.md` -> `docs/START_HERE.md` ->
  `docs/SETUP.md`) before `xpost-bridge.conf` will run at all -- the engine
  itself is not part of this template.
- Fill in every `REPLACE_WITH_*` placeholder in
  `system/supervisord.conf.d/xpost-bridge.conf`'s `environment=` line: your
  own Slack channel id, your own Discord channel and forum ids, a
  4-character operator id of your choosing, and (if you want bridge alerts)
  a private Slack channel id. The rest of that line (direction,
  single-instance, reaction mirroring, time source, log level, catch-up
  behavior, data/log/status paths, admin port) is a reasonable generic
  default and does not need to change.
- `data/xpost-bridge/backfill/tools/launch_classifiers.py` and
  `merge_sorting.py` hardcode a three-category sorting scheme
  (`help-and-bugs` / `general` / `show-and-tell`) and per-category quotas
  that matched the original operator's specific Discord channel topology.
  They are kept as a worked example, not generalized -- rewrite the
  categories (and the `QUOTA` dict in `merge_sorting.py`) to match your own
  channels before reusing these scripts for your own one-off backfill.
- The planned live-traffic classifier, manual routing overrides, and
  hardened cross-channel duplicate-prevention invariant mentioned above are
  not built anywhere yet -- not in this template, not in the live engine
  repo as of this snapshot. There is nothing to adapt for them yet; this is
  flagged here as future work, not a gap you need to close now.

## Environment

What this template needs INSTALLED, beyond what the template already has.
Declared in `template.toml`'s `[environment]` table; an adopting mind
converges it at ITS OWN pinned apt snapshot timestamp, so package versions come
out consistent with the rest of that mind's environment rather than frozen to
whatever this publisher happened to have.

Nothing extra -- runs on the stock workspace environment. The dashboard's
own dependencies (Flask, flask-sock, Werkzeug) are declared in its own
`pyproject.toml` and picked up by the stock template's normal `uv sync
--all-packages`. The bridge engine itself (Node/TypeScript, run via `tsx`)
is not part of this template's environment -- it lives entirely in its own
clone under `.external_worktrees/xpost-bridge/`, with its own `npm
install`.

## How to adapt it

Instructions for the NEXT agent -- the one adapting this template into a
new mind. This is the `use-template` skill's template path; in short:

1. Read this entire file first, especially "Requirements" below. It holds two
   kinds of entry and they are handled at different times: the machine-readable
   `requires_` lines are ACTIVATION (set them up before anything runs), and
   the prose bullets are ADAPTATION (decide or rewire them afterwards).
2. Present the template to the user in plain, non-technical language: what
   it is, what it does, and what it needs from them (name the activation
   requirements).
3. Ask whether they want to use the same connectors (e.g. their own Slack).
   If YES: ACTIVATE FIRST -- initiate every `requires_permission` line NOW
   via a latchkey permission request (see the `latchkey` skill; the request
   opens the approval/login flow in the minds app), wire up any
   `requires_secret` values, start the services, and get the app showing
   THE USER'S OWN DATA. Done for a data-backed app means the user can open it
   and see their own data -- NOT that a service starts or an endpoint returns
   200. Then tell them it is live and to take a look.
4. Only AFTER that (or immediately, if they chose different connectors -- the
   swap is then the first adaptation) ask: "How do you want to adapt it?"
5. Work through each requirement interactively, one at a time. Translate each
   into plain language, ask for a decision only when you genuinely need one,
   and resolve the obvious ones yourself.
6. When done, append a dated entry to "Adaptation history" below (never
   rewrite earlier entries) and commit.

## Publication history

This template's changelog: what each published version changed. The PUBLISHER
appends one entry per version (newest last); earlier entries are never rewritten.
This is distinct from "Adaptation history" below, which is the ADOPTERS' log.

### v1 (2026-10-01) -- first publish: the dashboard app, the two service
configs (ids genericized), and the backfill/repair tooling, with the bridge
engine itself referenced as a separate external repo

## Adaptation history

Each mind that adapts this template appends one dated entry below. Earlier
entries are never rewritten.
