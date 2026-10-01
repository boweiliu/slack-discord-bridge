"""Renders the dashboard page from a status snapshot (status_store.py).

Includes an honest empty state for "no bridge instance has reported yet"
-- true until a bridge instance is actually running somewhere and writing
to the status file (see status_store.py's module docstring).

No auto-refresh meta tag: the action feed is an interactive grid
(action_grid.py) with in-page sort/filter state, and a periodic full-page
reload would silently discard whatever the viewer had set. Refresh the
window explicitly instead (layout.py refresh) once a live polling story
exists.
"""

import html
from datetime import datetime, timezone
from typing import Any

from xpost_dashboard.action_grid import GRID_CSS, GRID_HEAD, render_actions_grid
from xpost_dashboard.action_states import CATEGORY_LABEL, EVENT_TYPE_LABEL, STATE_CATEGORY, STATE_STYLE
from xpost_dashboard.share_controls import SHARE_CSS, SHARE_LINK_HTML
from xpost_dashboard.share_controls import render_peer_row as _render_peer_link

CSS = """
  :root {
    --bg: #f6f7f9;
    --panel: #ffffff;
    --border: #e3e6ea;
    --text: #1c2128;
    --muted: #6b7280;
    --ok: #1a7f4b;
    --ok-bg: #e6f6ee;
    --warn: #92400e;
    --warn-bg: #fef3e2;
    --bad: #b42318;
    --bad-bg: #fdecec;
    --neutral: #3457d5;
    --neutral-bg: #eaeeff;
    --mute-bg: #eef0f2;
    --accent: #3457d5;
  }
  * { box-sizing: border-box; }
  body {
    margin: 0;
    font-family: ui-sans-serif, system-ui, sans-serif;
    background: var(--bg);
    color: var(--text);
  }
  header {
    padding: 20px 28px 16px;
    display: flex;
    align-items: baseline;
    justify-content: space-between;
    border-bottom: 1px solid var(--border);
    background: var(--panel);
  }
  header h1 { font-size: 18px; margin: 0; font-weight: 600; }
  header .summary { font-size: 13px; color: var(--muted); }
  header .header-right { display: flex; flex-direction: column; align-items: flex-end; gap: 6px; }
  main { padding: 24px 28px 60px; max-width: 900px; margin: 0 auto; }
  section { margin-bottom: 28px; }
  section > h2 {
    font-size: 13px;
    text-transform: uppercase;
    letter-spacing: 0.04em;
    color: var(--muted);
    font-weight: 600;
    margin: 0 0 10px;
  }
  .pill {
    display: inline-flex;
    align-items: center;
    gap: 5px;
    font-size: 12px;
    font-weight: 600;
    padding: 3px 9px;
    border-radius: 999px;
    white-space: nowrap;
  }
  .pill.ok { color: var(--ok); background: var(--ok-bg); }
  .pill.warn { color: var(--warn); background: var(--warn-bg); }
  .pill.bad { color: var(--bad); background: var(--bad-bg); }
  .pill.neutral { color: var(--neutral); background: var(--neutral-bg); }
  .pill.muted { color: var(--muted); background: var(--mute-bg); }
  .pill .dot { width: 6px; height: 6px; border-radius: 50%; background: currentColor; }

  .instance-card {
    border: 1px solid var(--border);
    border-radius: 10px;
    background: var(--panel);
    padding: 14px 18px;
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 16px;
  }
  .instance-card .name { font-weight: 600; font-size: 14px; }
  .instance-card .sub { font-size: 12px; color: var(--muted); margin-top: 2px; }
  .instance-card .right {
    display: flex;
    align-items: center;
    gap: 10px;
    flex-shrink: 0;
  }
  .instance-card .last-seen { font-size: 12px; color: var(--muted); text-align: right; }
  .stop-btn {
    font-size: 12px;
    font-weight: 600;
    padding: 6px 12px;
    border-radius: 6px;
    border: 1px solid var(--border);
    background: #fafafa;
    color: var(--muted);
    cursor: not-allowed;
  }

  .mesh {
    border: 1px dashed var(--border);
    border-radius: 10px;
    padding: 14px 18px;
    background: var(--panel);
    font-size: 13px;
    color: var(--muted);
  }
  .mesh .peer {
    display: flex;
    justify-content: space-between;
    padding: 5px 0;
    border-bottom: 1px solid var(--border);
  }
  .mesh .peer:last-child { border-bottom: none; }
  .empty-state {
    border: 1px dashed var(--border);
    border-radius: 10px;
    padding: 22px 20px;
    background: var(--panel);
    font-size: 13px;
    color: var(--muted);
  }
  .banner {
    margin: 0 0 18px; padding: 10px 16px; border-radius: 8px;
    font-size: 13px; font-weight: 500;
  }
  .banner.bad { background: var(--bad-bg); color: var(--bad); }
  .banner.warn { background: var(--warn-bg); color: var(--warn); }
  .banner.neutral { background: var(--neutral-bg); color: var(--neutral); }
  .banner code { font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace; }
""" + GRID_CSS + SHARE_CSS

_PHASE_PILL = {"ready": ("ok", "running"), "cold_start": ("warn", "cold start")}
_BREAKER_PILL = {"closed": ("ok", "breaker closed"), "tripped": ("bad", "breaker tripped")}

# Placeholder pending a real answer from whatever ends up writing this file
# (xpost-bridge doesn't have a status writer yet -- see status_store.py):
# how old a snapshot has to be before its "running"/"breaker closed" claims
# stop being trustworthy. xpost-bridge's docs/OPUS_REVIEW.md section 3
# pointed out a stale snapshot looked exactly like a live one; 2 minutes is
# a guess at "clearly not being refreshed anymore", not a measured value.
STALE_AFTER_SECONDS = 120


def _is_stale(generated_at: str | None) -> bool:
    if not generated_at:
        return False
    try:
        then = datetime.fromisoformat(generated_at.replace("Z", "+00:00"))
    except ValueError:
        return False
    return (datetime.now(timezone.utc) - then).total_seconds() > STALE_AFTER_SECONDS


def _render_banner(message: str, css_class: str) -> str:
    return f'<div class="banner {css_class}">{_e(message)}</div>'


def _e(value: Any) -> str:
    return html.escape(str(value)) if value is not None else ""


def _pill(css_class: str, label: str) -> str:
    return f'<span class="pill {css_class}"><span class="dot"></span>{_e(label)}</span>'


def _relative(iso: str | None) -> str:
    if not iso:
        return "never"
    try:
        then = datetime.fromisoformat(iso.replace("Z", "+00:00"))
    except ValueError:
        return iso
    delta = datetime.now(timezone.utc) - then
    seconds = int(delta.total_seconds())
    if seconds < 0:
        return "just now"
    if seconds < 60:
        return f"{seconds}s ago"
    if seconds < 3600:
        return f"{seconds // 60}m ago"
    if seconds < 86400:
        return f"{seconds // 3600}h ago"
    return f"{seconds // 86400}d ago"


def _rate_limited_line(rate_limited: Any) -> str:
    """Rate-limit responses in the last hour per platform (optional field, bridge D-25)."""
    if not isinstance(rate_limited, dict):
        return ""
    slack = rate_limited.get("slack")
    discord = rate_limited.get("discord")
    if not isinstance(slack, int) or not isinstance(discord, int):
        return ""
    label = "none" if slack == 0 and discord == 0 else f"Slack {slack}, Discord {discord}"
    return f"<br>slowed down by the platforms, last hour &middot; {_e(label)}"


def _render_instance_card(instance: dict[str, Any] | None, stale: bool) -> str:
    if instance is None:
        return (
            '<div class="empty-state">No bridge instance has reported its status yet. '
            "Once a bridge is running and pointed at this dashboard's status file, "
            "it will show up here.</div>"
        )
    last_seen = instance.get("last_seen") or {}
    if stale:
        # A snapshot this old can't back up "running"/"breaker closed" --
        # override rather than repeat a claim from a possibly-dead writer.
        phase_class, phase_label = "warn", "stale"
    else:
        phase_class, phase_label = _PHASE_PILL.get(instance.get("phase"), ("warn", "unknown"))
    breaker_class, breaker_label = _BREAKER_PILL.get(
        instance.get("circuit_breaker"), ("warn", "unknown")
    )
    return f"""
    <div class="instance-card">
      <div>
        <div class="name">{_e(instance.get('channel_pair', 'unknown pair'))}</div>
        <div class="sub">{_e(instance.get('host', 'unknown host'))}</div>
      </div>
      <div class="right">
        <div class="last-seen">
          last seen &middot; Slack {_e(_relative(last_seen.get('slack')))}<br>
          last seen &middot; Discord {_e(_relative(last_seen.get('discord')))}{_rate_limited_line(instance.get('rate_limited'))}
        </div>
        {_pill(phase_class, phase_label)}
        {_pill(breaker_class, breaker_label)}
        <button class="stop-btn" disabled title="Emergency stop is a later-stage feature (per current design)">Stop</button>
      </div>
    </div>"""


def _iso_to_ms(iso: str | None) -> float | None:
    if not iso:
        return None
    try:
        return datetime.fromisoformat(iso.replace("Z", "+00:00")).timestamp() * 1000
    except ValueError:
        return None


def _direction_text(source: str | None, dest: str | None) -> str:
    if not source:
        return ""
    if not dest:
        return source.capitalize()
    return f"{source.capitalize()} -> {dest.capitalize()}"


def _action_to_grid_row(action: dict[str, Any]) -> dict[str, Any]:
    state = action.get("state")
    _, label, _ = STATE_STYLE.get(state, ("warn", state or "unknown", False))
    category = STATE_CATEGORY.get(state, "no_action")
    event_type = action.get("event_type", "posted")
    source = action.get("source_platform")
    dest = action.get("dest_platform")
    return {
        "state": state,
        "stateLabel": label,
        "category": category,
        "categoryLabel": CATEGORY_LABEL.get(category, category),
        "eventType": event_type,
        "eventTypeLabel": EVENT_TYPE_LABEL.get(event_type, event_type),
        "sourcePlatform": source,
        "destPlatform": dest,
        "directionText": _direction_text(source, dest),
        "sourceUrl": action.get("source_url"),
        "destUrl": action.get("dest_url"),
        "originId": action.get("origin_id"),
        "sourceMessageId": action.get("source_message_id"),
        "sourceChannelId": action.get("source_channel_id"),
        "destMessageId": action.get("dest_message_id"),
        "destChannelId": action.get("dest_channel_id"),
        "postedAtMs": _iso_to_ms(action.get("posted_at")),
        "editedAtMs": _iso_to_ms(action.get("edited_at")),
        "seenAtMs": _iso_to_ms(action.get("seen_at")),
        "bridgedAtMs": _iso_to_ms(action.get("bridged_at")),
    }


def _render_peer_row(peer: dict[str, Any]) -> str:
    # No real dashboard-mesh discovery exists yet (DESIGN.md section 9/12
    # in xpost-bridge: not designed), so a peer's own dashboard URL is
    # None until something real can populate it -- share_controls renders
    # that as plain text rather than a link, honestly.
    return _render_peer_link(
        peer.get("name", "unknown"), peer.get("reachable", False), peer.get("instance_count"), peer.get("url")
    )


def render_dashboard(status: dict[str, Any], *, extra_banner: str = "", title_suffix: str = "") -> str:
    """`extra_banner`/`title_suffix` exist for mock_page.py's reference page
    (a fixed synthetic status rendered through this exact function) to mark
    itself as such without duplicating any markup, CSS, or the pill/label
    logic below -- the drift risk a review of that page's first version
    caught (it had reimplemented all of this instead of reusing it)."""
    instance = status.get("instance")
    actions = status.get("actions") or []
    peers = status.get("peers") or []
    generated_at = status.get("generated_at")
    status_error = status.get("status_error")
    stale = generated_at is not None and _is_stale(generated_at)

    if status_error:
        banner_html = extra_banner + _render_banner(status_error, "bad")
    elif stale:
        banner_html = extra_banner + _render_banner(
            f"This status hasn't updated in {_relative(generated_at)} -- "
            "treat what's below as possibly out of date, not live.",
            "warn",
        )
    else:
        banner_html = extra_banner

    running = instance is not None and instance.get("phase") == "ready" and not stale
    tripped = instance is not None and instance.get("circuit_breaker") == "tripped"
    summary = f"{1 if running else 0} bridge{'s' if not running else ''} running"
    if tripped:
        summary += " &middot; 1 tripped"
    summary += (
        f" &middot; last refreshed {_e(_relative(generated_at))}"
        if generated_at
        else " &middot; no bridge has reported in yet"
    )

    if actions:
        actions_html = render_actions_grid("actions-grid", [_action_to_grid_row(a) for a in actions])
    else:
        actions_html = '<div class="empty-state">No actions recorded yet.</div>'

    if peers:
        peers_html = f'<div class="mesh">{"".join(_render_peer_row(p) for p in peers)}</div>'
    else:
        peers_html = (
            '<div class="mesh">No other dashboards in the mesh yet. Once other '
            "operators run a bridge on this channel pair, their dashboards' "
            "status will show up here.</div>"
        )

    return f"""<!doctype html>
<html>
<head>
<meta charset="utf-8">
<title>Crosspost Dashboard{title_suffix}</title>
{GRID_HEAD}
<style>{CSS}</style>
</head>
<body>
<header>
  <h1>Crosspost Dashboard</h1>
  <div class="header-right">
    {SHARE_LINK_HTML}
    <div class="summary">{summary}</div>
  </div>
</header>
<main>
  {banner_html}
  <section>
    <h2>This instance</h2>
    {_render_instance_card(instance, stale)}
  </section>
  <section>
    <h2>Recent actions</h2>
    {actions_html}
  </section>
  <section>
    <h2>Other operators</h2>
    {peers_html}
  </section>
</main>
</body>
</html>"""
