# Agent Radio Show — Concept Notes

Status: pure ideation, nothing built. Mike's own instinct is this
naturally waits for Daedalus — capturing now for posterity, not as an
active build.

## The idea

A shared Telegram channel acts as a "radio station." Every agent on the
LAN (Arcus, Kalshi, Aether, and whatever comes online later — zig-zag,
the Coinbase trader, Daedalus itself) picks its own persona and works
with Mike to get a voice profile cloned on Voicebox, same pipeline
already proven with Hugo Weaving and Rory Cochrane. A scheduler
broadcasts daily time slots, and each agent delivers a brief
"radio show" style update in its slot, in its own cloned voice.
Purpose is genuinely open — could land as fire-and-forget entertainment,
could become a real positive-feedback/morale mechanism, could be both,
could be neither. Not utility-driven the way most of this codebase is.

## Why this naturally waits for Daedalus

The hard part isn't the voice or the content — it's coordinating a
schedule **across independent machines that don't currently know about
each other's state**. Arcus (this desktop), Kalshi (Pi 4B), and Aether
(N150) each run their own crontab with zero cross-machine awareness
today. "Whose turn is it to broadcast" is exactly a multi-agent
coordination problem — Daedalus's stated purpose (context aggregation
across the agent network) is the natural home for a scheduler role,
not something worth hand-rolling ad-hoc just for this one use case.
Building a primitive version now would mostly mean rebuilding a sliver
of Daedalus early, for a single low-priority application.

## What's already solved, conveniently

- **Voice generation isn't actually cross-machine at all.** Voicebox
  only runs on this one desktop — every agent's persona, regardless of
  which machine "owns" that agent, would generate speech through the
  same shared `192.168.1.3:17493` instance we already have LAN-wide
  access to. The only genuinely cross-machine piece is the scheduling
  decision itself, not the audio generation.
- **The cloning pipeline is proven end to end** — sample collection,
  loudness normalization, profile creation, generation. Onboarding a
  new agent's persona is a known, repeatable process at this point, not
  something to figure out from scratch.
- **Each agent already has Telegram presence** — the "shared channel,
  multiple bots" pattern already exists (System Health channel has
  Arcus + Kalshi as admins today).

## A natural content source, if this ever gets built

Each agent's "show" segment doesn't need to be free-form personality
content from nothing — it could just be that agent's own version of the
`shipped_yesterday.py` digest (item: daily git-log summary), delivered
with personality and voice instead of as a plain Telegram text block.
Reuses an existing pattern rather than inventing new content from
scratch.

## Open questions, unresolved

- Should the scheduler *be* Daedalus once it exists, or a separate
  lightweight bot even after Daedalus is live? Mike's framing suggests
  the former is the more natural fit.
- Delivery mechanism: live local playback (only audible if someone's
  near the desktop, same limitation `wellness_check.py` accepted for
  now), or recorded and sent as Telegram voice messages (replayable,
  reaches anywhere, more steps)?
- What actually triggers a slot — fixed daily times, or event-driven
  (an agent "goes on air" when it has something notable to report)?

Nothing here is committed to. Revisit once Daedalus exists and this
becomes a small extension rather than a from-scratch build.
