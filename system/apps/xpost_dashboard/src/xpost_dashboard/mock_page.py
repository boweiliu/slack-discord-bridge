"""Reference page: a fully populated view of the dashboard, with made-up
example rows instead of real data.

Not the live "/" page -- serves at "/mock" as documentation of the
intended look once a bridge is actually reporting, since the real page is
honestly empty until then (no bridge writes to it yet; see
status_store.py). Built by handing a synthetic, schema-shaped status dict
to render.py's `render_dashboard` -- the exact function "/" uses -- rather
than reimplementing any markup, CSS, or label logic here. An earlier
version did reimplement all of that by hand; a review caught it as a
drift risk (a future change to render.py's layout or CSS would go
unnoticed here, so this page could show stale markup while claiming to
document the current one) and this is the fix.
"""

from datetime import datetime, timedelta, timezone

from xpost_dashboard.render import render_dashboard

# Synthetic example ids, chosen only to look like the real Slack/Discord id
# formats -- not actual channel ids.
_CHANNEL_ID = {"slack": "C000000000", "discord": "100000000000000001"}

_REFERENCE_BANNER = (
    '<div class="banner neutral">Reference page, not live data -- shows what this '
    "dashboard looks like once a bridge is actually reporting to it. "
    'The real page is at <code>/</code>.</div>'
)


def _iso(now: datetime, seconds_ago: float | None) -> str | None:
    return None if seconds_ago is None else (now - timedelta(seconds=seconds_ago)).isoformat()


def _mock_action(
    now: datetime,
    state: str,
    source: str,
    dest: str | None,
    *,
    posted_s_ago: float | None,
    edited_s_ago: float | None = None,
    seen_s_ago: float | None,
    bridged_s_ago: float | None,
    source_url: str | None = None,
    dest_url: str | None = None,
    source_message_id: str,
    dest_message_id: str | None = None,
    event_type: str = "posted",
) -> dict:
    source_channel_id = _CHANNEL_ID[source]
    dest_channel_id = _CHANNEL_ID[dest] if dest else None
    return {
        "state": state,
        "event_type": event_type,
        "source_platform": source,
        "dest_platform": dest,
        "source_url": source_url,
        "dest_url": dest_url,
        "origin_id": f"{source}:{source_channel_id}:{source_message_id}",
        "source_message_id": source_message_id,
        "source_channel_id": source_channel_id,
        "dest_message_id": dest_message_id,
        "dest_channel_id": dest_channel_id,
        "posted_at": _iso(now, posted_s_ago),
        "edited_at": _iso(now, edited_s_ago),
        "seen_at": _iso(now, seen_s_ago),
        "bridged_at": _iso(now, bridged_s_ago),
    }


def _mock_status() -> dict:
    now = datetime.now(timezone.utc)
    actions = [
        _mock_action(
            now, "detected", "slack", "discord",
            posted_s_ago=3, seen_s_ago=2, bridged_s_ago=None,
            source_url="#", source_message_id="1738020001.000200",
        ),
        _mock_action(
            now, "bridged", "slack", "discord",
            posted_s_ago=16, seen_s_ago=15, bridged_s_ago=14,
            source_url="#", dest_url="#",
            source_message_id="1738019988.000300", dest_message_id="1147920012345678901",
        ),
        _mock_action(
            now, "bridged", "slack", "discord",
            posted_s_ago=95, edited_s_ago=20, seen_s_ago=94, bridged_s_ago=93,
            source_url="#", dest_url="#", event_type="edited",
            source_message_id="1738019909.000500", dest_message_id="1147920011122334455",
        ),
        _mock_action(
            now, "bridged_by_peer", "discord", "slack",
            posted_s_ago=44, seen_s_ago=43, bridged_s_ago=41,
            source_url="#", dest_url="#",
            source_message_id="1147920098765432109", dest_message_id="1738019960.000100",
        ),
        _mock_action(
            now, "copy_observed", "discord", None,
            posted_s_ago=None, seen_s_ago=60, bridged_s_ago=None,
            source_message_id="1147920098765432200",
        ),
        _mock_action(
            now, "not_my_turn", "discord", "slack",
            posted_s_ago=70, seen_s_ago=69, bridged_s_ago=None,
            source_url="#", source_message_id="1147920098765431900",
        ),
        _mock_action(
            now, "reserved", "discord", "slack",
            posted_s_ago=88, seen_s_ago=87, bridged_s_ago=None,
            source_url="#", source_message_id="1147920098765431850",
        ),
        _mock_action(
            now, "missed", "discord", "slack",
            posted_s_ago=125, seen_s_ago=122, bridged_s_ago=None,
            source_url="#", source_message_id="1147920098765431800",
        ),
        _mock_action(
            now, "ignored_automated", "slack", None,
            posted_s_ago=185, seen_s_ago=184, bridged_s_ago=None,
            source_message_id="1738019839.000700",
        ),
        _mock_action(
            now, "ignored_duplicate", "slack", None,
            posted_s_ago=245, seen_s_ago=241, bridged_s_ago=None,
            source_message_id="1738019779.000900",
        ),
        _mock_action(
            now, "ignored_echo_text", "discord", None,
            posted_s_ago=370, seen_s_ago=368, bridged_s_ago=None,
            source_message_id="1147920098765430500",
        ),
        _mock_action(
            now, "ignored_cold_start", "slack", None,
            posted_s_ago=1100, seen_s_ago=1080, bridged_s_ago=None,
            source_message_id="1738018709.001100",
        ),
        _mock_action(
            now, "ignored_breaker_tripped", "discord", None,
            posted_s_ago=7300, seen_s_ago=7290, bridged_s_ago=None,
            source_message_id="1147920098765420100",
        ),
    ]
    return {
        "schema_version": 6,
        "generated_at": now.isoformat(),
        "instance": {
            "id": "reference-instance",
            "channel_pair": "Slack #general <-> Discord help-and-bugs",
            "host": "host-a",
            "phase": "ready",
            "circuit_breaker": "closed",
            "last_seen": {"slack": _iso(now, 4), "discord": _iso(now, 11)},
        },
        "actions": actions,
        "peers": [
            {"name": "host-b", "reachable": True, "instance_count": 1,
             "url": "https://xpost-dashboard.host-b.example/"},
            {"name": "host-c", "reachable": False, "instance_count": None,
             "url": "https://xpost-dashboard.host-c.example/"},
        ],
    }


def build_mock_page() -> str:
    return render_dashboard(_mock_status(), extra_banner=_REFERENCE_BANNER, title_suffix=" (reference)")
