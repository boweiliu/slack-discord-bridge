"""Reads and writes the dashboard's status snapshot.

The dashboard is a pure observer (docs/DESIGN.md section 9 in the
xpost-bridge project: "dashboards observe bridges ... and never send
anything that changes what a bridge does"). It never talks to a bridge
instance directly -- a bridge instance (or a small poller run alongside
it) writes a snapshot to ``STATUS_FILE`` on whatever cadence it likes, and
this module just reads whatever is there. As of 2026-09-28 no bridge
instance has an endpoint that writes this file yet -- ``load_status``
returning an empty snapshot is the honest result of that, not a bug.

Schema (version 6 -- drops ``snippet``; xpost-bridge's own
`docs/OPUS_REVIEW.md` section 3 (2026-09-28, written after reviewing this
file at commit b3dcc99d4) flagged that the bridge deliberately keeps user
message text out of everything it writes to disk or logs at info level
(see xpost-bridge's `src/log.ts`), and this file was the one place in the
whole system that didn't. The review's larger point -- that the producer
(xpost-bridge) should own this contract via a real `docs/status.schema.json`
once it builds the status writer, not this file -- is not yet acted on;
``instance.channel_pair`` in particular is known-wrong (the real topology
is three Discord channels into one Slack channel, not a pair --
xpost-bridge's `docs/practical/CHANNEL_TOPOLOGY.md`) and is left as-is
pending that. Version 5 added an optional ``url`` per peer, for linking
out to its dashboard; version 4 added per-action IDs (internal and
platform-native) and an event type; version 3 added one instance per
dashboard, a per-message action feed instead of aggregate rates, and
four separate timestamps per action instead of one flat "when"; see
action_states.py for the ten ``state`` values, pulled directly from
xpost-bridge's decision.ts, and the ``STATE_CATEGORY``/``CATEGORY_LABEL``
maps used to derive ``category`` below):

    {
      "schema_version": 6,
      "generated_at": "<ISO-8601 UTC>",
      "instance": {
        "id": str,
        "channel_pair": str,           # human label, e.g. "Slack #x <-> Discord y"
        "host": str,
        "phase": "cold_start" | "ready",
        "circuit_breaker": "closed" | "tripped",
        "last_seen": {"slack": str | null, "discord": str | null}  # ISO-8601
      } | null,
      "actions": [
        {
          "state": str,                     # a key in action_states.STATE_STYLE
          # "posted" for every real row today -- edited_at/deleted-style
          # rows are schema-ready but the bridge doesn't detect edits or
          # deletes yet (docs/ROBUSTNESS.md lists both as future scope).
          "event_type": "posted" | "edited" | "deleted",
          "source_platform": "slack" | "discord",
          "dest_platform": "slack" | "discord" | null,  # null for observe-only states
          # No message text anywhere in this contract, deliberately -- link
          # out via source_url/dest_url instead of persisting/displaying it.
          "source_url": str | null,
          "dest_url": str | null,
          # tags.ts's originId(platform, channelId, messageId), e.g.
          # "slack:C000000000:1738020001.000200" -- the same id the
          # bridge's own OriginLedger/turn-taking code uses internally.
          "origin_id": str,
          "source_message_id": str,
          "source_channel_id": str,
          "dest_message_id": str | null,   # the copy's own platform id, once it exists
          "dest_channel_id": str | null,
          # Four distinct moments, all ISO-8601 or null:
          "posted_at": str | null,   # the original's own platform timestamp
          "edited_at": str | null,   # last edit on the source platform, if any
                                      # (edits aren't tracked by the bridge yet --
                                      # always null until that ships)
          "seen_at": str | null,     # when this instance's event handler fired
          "bridged_at": str | null,  # when the copy was actually posted
                                      # (by us, or -- best effort -- by the peer
                                      # whose copy we found)
        }
      ],
      "peers": [
        {
          "name": str,
          "reachable": bool,
          "instance_count": int | null,
          # None until dashboard-mesh discovery/connectivity is designed
          # (xpost-bridge DESIGN.md section 9/12: not yet) -- there is
          # nowhere real for this to point today.
          "url": str | null,
        }
      ]
    }
"""

import json
import os
from pathlib import Path
from typing import Any

DATA_DIR = Path(os.environ.get("XPOST_DASHBOARD_DATA_DIR", "data/.apps/xpost-dashboard"))
STATUS_FILE = DATA_DIR / "status.json"

SCHEMA_VERSION = 6

EMPTY_STATUS: dict[str, Any] = {
    "schema_version": SCHEMA_VERSION,
    "generated_at": None,
    "instance": None,
    "actions": [],
    "peers": [],
}


def load_status() -> dict[str, Any]:
    """Return the latest snapshot, or an empty one if nothing has reported yet.

    A file that exists but can't be used (bad JSON, wrong shape, or a
    schema version this dashboard doesn't speak) is a different situation
    from nothing having reported at all -- something IS writing, just not
    something this dashboard can read. Collapsing that into the same empty
    state was flagged in xpost-bridge's docs/OPUS_REVIEW.md section 3 as
    the exact silent-failure pattern this tool exists to catch: an
    incompatible producer looked like an idle one. The returned dict
    carries a ``status_error`` string when that's what happened; the empty
    dashboard state otherwise means what it says.
    """
    if not STATUS_FILE.is_file():
        return dict(EMPTY_STATUS)
    try:
        with STATUS_FILE.open() as f:
            data = json.load(f)
    except (OSError, json.JSONDecodeError):
        return {
            **EMPTY_STATUS,
            "status_error": "The status file exists but isn't valid JSON.",
        }
    if not isinstance(data, dict):
        return {
            **EMPTY_STATUS,
            "status_error": "The status file exists but isn't in the expected format (not a JSON object).",
        }
    found_version = data.get("schema_version")
    if found_version != SCHEMA_VERSION:
        return {
            **EMPTY_STATUS,
            "status_error": (
                f"The status file is schema version {found_version!r}, but this dashboard "
                f"reads version {SCHEMA_VERSION}. Whatever is writing it needs to update, or "
                "this dashboard does -- they've drifted apart."
            ),
        }
    return data


def write_status(status: dict[str, Any]) -> None:
    """Persist a snapshot. Used by tests and by any local poller/fixture script."""
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    tmp = STATUS_FILE.with_suffix(".json.tmp")
    with tmp.open("w") as f:
        json.dump(status, f, indent=2)
    tmp.replace(STATUS_FILE)
