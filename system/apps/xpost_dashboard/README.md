# xpost-dashboard

Monitoring and control plane for the Slack/Discord crosspost bridges
(the [xpost-bridge](https://github.com/imbue-ai/xpost-bridge) project,
`docs/DESIGN.md` section 9 there).

`/` serves the real, data-driven page (`render.py` + `status_store.py`).
`/mock` serves a fully populated reference page (`mock_page.py`) -- not
live data, documentation of what `/` looks like once a bridge is actually
reporting, since `/` is honestly empty until then. It reads its labels
from `action_states.py` rather than hardcoding them, so it can't drift
from what `/` would actually show.

## Status contract

This app is a pure observer: it never talks to a bridge instance, it only
reads a JSON snapshot from `XPOST_DASHBOARD_DATA_DIR/status.json` (see
`status_store.py` for the full schema and `write_status()` for the write
side). A bridge instance -- or a small poller run alongside it -- is
expected to write that file on its own cadence. As of 2026-09-28 no such
writer exists yet in xpost-bridge, so the dashboard's honest current state
is the empty one ("no bridge instance has reported yet"), not a bug.
