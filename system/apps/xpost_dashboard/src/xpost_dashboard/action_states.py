"""The full set of per-message states the dashboard can show.

Pulled from xpost-bridge's decision logic; since 2026-09-30 the bridge owns
this list (`ActionState` in its `src/bridge.ts`, contract in its
`docs/status.schema.md`): `not_my_turn` (another member's slot) and
`reserved` (slot 0 held for a joining bridge, its D-21) were added then.
Older note (as of commit ac6561c),
not invented: the four `PostOutcome` values in `src/decision.ts` cover what
happens once a message is a turn-taking candidate, and the six
`SkipReason` values cover the ways a message never becomes one.

    PostOutcome ("post" | "lost-race" | "slot-expired")
    SkipReason ("automated" | "already-a-copy" | "tag-marker-in-text"
                | "breaker-tripped" | "not-ready-for-live-traffic"
                | "duplicate-delivery")

"detected" has no direct code equivalent -- it is the dashboard's label for
an eligible message that has entered turn-taking but not yet resolved to
one of the outcomes above (i.e. `classifyIncoming` said eligible, decision
pending). "copy_observed" corresponds to the `already-a-copy` skip reason,
labeled for what it actually does (passive liveness learning,
docs/ROBUSTNESS.md C3) rather than the skip mechanics.

Each entry: (css class, display label, has a destination platform).
A state with no destination is something the instance only *observed* --
there was no bridging attempt with a direction to show.

Labels describe what THIS INSTANCE decided, not a fact about the message.
xpost-bridge's docs/OPUS_REVIEW.md section 3 caught the original labels
claiming more than that: "bridged_by_peer" and "missed" read as delivery
facts, but a lost-race or slot-expiry is one candidate standing down --
with N instances watching, a message an instance sees as "missed" is
normally posted by another candidate 5 seconds later. Only the platforms
know whether a message actually made it across (the not-yet-built
catch-up sweep, DESIGN.md section 7); a per-instance feed can honestly
show only its own decisions. "Stood down" replaces the delivery-flavored
wording below for exactly that reason.
"""

STATE_STYLE: dict[str, tuple[str, str, bool]] = {
    "detected": ("neutral", "Detected", True),
    "bridged": ("ok", "Bridged", True),
    "bridged_by_peer": ("ok", "Stood down (peer already posted)", True),
    "not_my_turn": ("muted", "Not my turn", True),
    "reserved": ("muted", "Stood down (a bridge was joining)", True),
    "missed": ("warn", "Stood down (slot passed)", True),
    "copy_observed": ("muted", "Copy observed", False),
    "ignored_automated": ("muted", "Ignored – automated", False),
    "ignored_echo_text": ("muted", "Ignored – echoed text", False),
    "ignored_duplicate": ("muted", "Ignored – duplicate", False),
    "ignored_cold_start": ("warn", "Ignored – cold start", False),
    "ignored_breaker_tripped": ("bad", "Ignored – breaker tripped", False),
}

# The coarse "did THIS INSTANCE do anything about this message" filter, for
# anyone who wants that answer without knowing all ten states. Deliberately
# not "was the message bridged" (see the module docstring) -- that a peer
# "already posted" or a slot "passed" is knowable and true regardless of
# what actually happened on the far side; whether the message made it
# across is not, and isn't claimed here.
#   acted      -- this instance itself posted a copy ("bridged" only)
#   pending    -- still being decided (only "detected")
#   no_action  -- everything else: this instance did not post a copy,
#                 whatever else may or may not be true of the message
CATEGORY_LABEL: dict[str, str] = {"acted": "Acted", "no_action": "No action", "pending": "Pending"}
EVENT_TYPE_LABEL: dict[str, str] = {"posted": "Posted", "edited": "Edited", "deleted": "Deleted"}

STATE_CATEGORY: dict[str, str] = {
    "detected": "pending",
    "bridged": "acted",
    "bridged_by_peer": "no_action",
    "not_my_turn": "no_action",
    "reserved": "no_action",
    "missed": "no_action",
    "copy_observed": "no_action",
    "ignored_automated": "no_action",
    "ignored_echo_text": "no_action",
    "ignored_duplicate": "no_action",
    "ignored_cold_start": "no_action",
    "ignored_breaker_tripped": "no_action",
}
