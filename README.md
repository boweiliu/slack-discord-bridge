<p align="center">
  <img alt="Slack-Discord bridge" src="template.svg" width="480">
</p>

# Slack-Discord bridge

<p align="center">
  <a href="https://boweiliu.github.io/open-in-minds/?git_url=https://github.com/boweiliu/slack-discord-bridge"><img alt="Open in Mind" height="64" src="https://img.shields.io/badge/Open%20in%20Mind-D8D1C0?style=for-the-badge"></a>
</p>

Didn't work? Create a Mind workspace and paste this to your agent:
` /use-template https://github.com/boweiliu/slack-discord-bridge`

## Why you care

**This is a pre-classifier v1 snapshot** -- it copies every message
verbatim, both directions, with no live-traffic sorting, no manual routing
overrides, and no hardened cross-channel duplicate-prevention yet. If your
team lives partly on Slack and partly on Discord, people on each side miss
what happens on the other, and someone ends up manually cross-posting or
just not seeing it at all. This template runs a bridge that copies messages
both ways in real time, plus a dashboard so you can see at a glance that
it's actually working.

**The actual bridge engine is a separate repo**, deliberately not copied
into this template: [`github.com/imbue-ai/xpost-bridge`](https://github.com/imbue-ai/xpost-bridge)
(private -- you'll need your own access or your own fork). This repo gives
you the operator-side pieces: the dashboard, the service configs to run it,
and some one-off tooling for migrating message history.

## How to use it

1. Clone `github.com/imbue-ai/xpost-bridge` and follow its own setup docs
   to create a Slack app and a Discord bot and get your credentials.
2. Fill in the `REPLACE_WITH_*` placeholders in
   `system/supervisord.conf.d/xpost-bridge.conf` with your own channel and
   operator ids, then start both the `xpost-bridge` and `xpost-dashboard`
   services.
3. Open the dashboard. `/` shows live activity once the bridge is running
   and reporting -- every message copied, when, and whether anything is
   stuck; `/mock` shows a fully populated example so you know what it will
   look like.
4. Post a message in either platform's connected channel and watch it show
   up on the other side, and in the dashboard.
5. If you have a backlog of existing Slack history you want copied over
   once, `data/xpost-bridge/backfill/tools/` has scripts for chunking it
   into classification workers, merging their verdicts, and auditing or
   repairing the Discord side afterwards.

## Ideas for making it yours

- Point the bridge at your own Slack channel and Discord channels/forum
  instead of the placeholder ids.
- Rework the three-category sorting scheme in the backfill tools
  (`help-and-bugs` / `general` / `show-and-tell`) to match your own
  channel topology.
- Add a second Discord server, or a second Slack channel, as another
  bridge instance -- instances don't share state, so they run
  independently.
- Build the live-traffic classifier this snapshot doesn't have yet: route
  incoming messages into different Discord channels based on content
  instead of mirroring everything into the same ones.
- Add manual routing overrides so a person can redirect a specific thread
  without waiting on a classifier.

## What this is

This repository is a published **minds template**: a clean, bootable
snapshot of what a mind built, ready to adapt into your own. It is NOT the
generic workspace template -- it is this specific project.

[`template.md`](template.md) is the full manifest -- what it is, how it
works, what it needs to run, and what to adapt -- with the
machine-readable half (recipe, requirements, and the environment it needs
installed) in [`template.toml`](template.toml).
