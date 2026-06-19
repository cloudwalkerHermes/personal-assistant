# Household/Life Backlog — Design Spec

Status: designed, not yet built (as of 2026-06-19)

## Origin

Reframes household/life friction as a boring, low-stakes ticket system —
the same psychological mechanism SRE/ops culture uses to strip emotional
charge from incidents. A ticket is a fact, not a referendum on anyone's
effort or character.

## Hierarchy

Storage: plain markdown files with YAML frontmatter, in real nested
folders (not labels/tags faking a hierarchy).

```
Backlog/
  Household/
  Agents/
    Arcus/
    Kalshi/
    Aether/
    ... (grows as the agent fleet grows)
  Estate/
  Personal/
  Carla/        (reserved — not active; for if she ever wants her own items)
```

`Agents` is a peer to `Household`/`Estate`/`Personal`/`Carla`, not each
individual agent — matches how attention actually gets allocated
("agent work vs. household work" is the first decision, which agent is
the second), not an org chart.

## Item schema (YAML frontmatter)

```yaml
priority: high | low
status: open | deferred | closed
created_by: <name>
created_date: <date>
```
Body of the markdown file = free-text description.

No due date field by default. Only attach a real date when there's a
genuine external constraint (company coming, seasonal deadline) — never
as default aspirational pressure. A missed due date reintroduces the
exact guilt cycle this system exists to avoid.

## Status semantics

- `Open` + priority shown (`Open-High` / `Open-Low`) while active
- `Deferred` — an active decision to not act right now. This is
  permission, not failure — distinct from leaving something open
  forever. Priority drops away once deferred (stops mattering).
- `Closed` — done. Priority drops away here too.

## Creation mechanism

Two tiers, cheap one first:

1. **Structured shorthand via Telegram** (no LLM, ships independent of
   anything else) — e.g. `new: household | high | Prep kitchen for new
   fridge`. Pure string parsing.
2. **Full natural language** — folds into roadmap item 16 (Arcus NL
   memory system) once that's unblocked (needs separate Claude API
   key). Same parsing layer, backlog creation becomes one more intent
   it handles.

**Receiving inbound Telegram messages** is the one piece of genuinely
new infrastructure (everything else built so far is outbound-only).
Avoid a persistent listener service or public webhook — instead reuse
the existing cron pattern (`system_health.py`'s shape): a cron job
polls Telegram's `getUpdates` every few minutes against a dedicated
"Backlog Inbox" channel/topic, parses anything new, writes the
markdown file.

## Update mechanism (defer / close / reopen)

Telegram DM, semi-structured: e.g. *"Arcus set DEFERRED status for
backlog task Household | kitchen fridge."*

- Category narrows the search to one folder.
- Fuzzy string match (e.g. `thefuzz`/`difflib` — no LLM needed) against
  item titles within that folder.
- Confident single match → apply the change, reply with confirmation
  ("✅ Deferred: Household — Prep kitchen for new fridge").
- Ambiguous (no confident match, or multiple close scores) → reply
  asking which item, rather than guessing wrong.

## Google Tasks sync

Local markdown is the source of truth for creation, priority, category,
created_by/date. Sync is two-way for completion, one-way for defer
(GCal has no "defer" concept — only done/not-done).

| Local state | GCal Tasks state |
|---|---|
| Open (High/Low) | Present, starred if High, unstarred if Low |
| Deferred | Removed (same rule as Closed — only Open items are mirrored) |
| Closed | Removed |
| Reopened (Deferred/Closed → Open) | Reappears |

- **Priority** → GCal's native **starred** feature (High = starred, Low
  = unstarred). No title-prefix hacks.
- **Category** → GCal's native **separate task lists**, one per
  top-level category (Household / Agents / Estate / Personal / Carla).
- **Agents sub-hierarchy** flattens into one GCal "Agents" list with a
  `[AgentName]` prefix in the title (e.g. `[Kalshi] Fix prop scanner
  threshold`) — full depth stays local-only, avoids GCal list sprawl.
- **Completion two-way**: ticking a task in GCal closes the real local
  item (no separate "remember to close it for real later" step);
  closing locally removes/ticks the GCal task.
- **Creating from GCal side**: also supported, for the "bored at the
  doctor's office" use case.
  - Category = whichever GCal list it was added to.
  - Priority = star state (star = High, no star = Low).
  - `created_by` defaults to `Mike` (no field for this in GCal Tasks).
  - Items added to the Agents list **without** an `[AgentName]` prefix
    fall back to `Agents/Uncategorized` locally.

## Open / deferred questions

- Storage backend is decided (markdown + frontmatter, real folders) —
  optionally a private git repo later for free audit history via
  commits, not required to start.
- Whether `Carla` category ever becomes active depends on whether she
  wants to participate — not assumed, just reserved.
