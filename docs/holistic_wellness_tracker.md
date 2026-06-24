# Holistic Wellness Tracker — Concept Notes

Status: pure ideation, nothing built, nothing decided. Jotted down for
later — see roadmap item 23 in `project_personal_assistant.md` memory.

## The original idea

Garmin-based physical monitoring (composite score, 3-day anomaly
detection, midday check-in) only sees biometrics — it can't tell the
difference between "running low because I'm pushing hard on something
intentional" and "running low because I'm actually struggling." Those
look identical to a wearable but call for very different responses.

The original framing: snap a photo of morning pages, have vision infer
a holistic state, use that to calibrate the midday check-in's tone —
more cautionary if physically-low-but-holistically-fine ("optimization
phase"), more forceful if physically-low-and-holistically-concerning
("spiraling").

## Why morning pages specifically is the wrong input

Morning pages work *because* they're unselfconscious — that's the
mechanism Julia Cameron's method is built on. Monitoring them risks
changing how freely they get written, undermining the practice itself.
Also a real accuracy risk either direction: venting through writing is
healthy and could misread as "spiraling" to a naive analysis; someone
actually struggling can write something that sounds composed. Wrong in
either direction has a real cost — false alarm on a fine day, or too
soft a touch on a day that needed more.

## Refined direction — separate voice check-in, not a repurposed journal

Rather than photographing morning pages, do a **separate, dedicated
digital check-in** during the same AM routine (coffee, journal time) —
explicitly for this purpose from the start, so there's no
expectation-of-privacy to violate. Two candidate channels:

- **Voicebox locally** — dictation hotkey (confirmed feature) during
  the morning routine. Voicebox also has a "Stories" feature
  (`/stories` endpoints) but that looked like an *output* composition
  tool (arranging generated clips into a timeline) based on earlier
  research, not an input/capture mechanism — needs verifying directly
  in the app before assuming it's the right tab for this.
- **Telegram voice message to Arcus** — same dictation content, just
  routed through the existing Telegram channel instead of staying
  local. Simpler to pipe into the existing alert infrastructure since
  everything else already flows through Telegram.

## The actual signal: prosody, not content

Pitch and pace (voice prosody) instead of transcribed sentiment —
harder to consciously perform/mask than word choice, which is part of
why this feels like a better-calibrated signal than reading content
for tone. **Important technical note**: Voicebox's own API doesn't
expose pitch/pace metrics — `/transcribe` gives text, not prosodic
features. Extracting actual pitch/pace would need a separate audio
analysis step on the raw recording (e.g. `librosa.pyin` for pitch
tracking; pace derivable from word count over clip duration once
transcribed). Not available off the shelf from Voicebox alone.

## Combine with Garmin stress score

Layer prosody-derived signal alongside Garmin's existing stress score
(already captured in `garmin_daily`, not currently weighted into the
wellness composite) as a second physical-adjacent input, distinct from
the sleep/battery/RHR composite already in use.

## Open questions, unresolved

- Does Voicebox's Stories tab actually support input/capture, or is it
  output-only? Needs hands-on verification before assuming it's usable
  here.
- How would "optimization phase" vs. "spiraling" actually get
  classified from pitch/pace + stress score? This is even less
  validated than text-sentiment inference was — no established
  methodology assumed here, would need real experimentation.
- Does a dedicated, explicitly-for-this-purpose voice check-in actually
  avoid the privacy/effectiveness tension morning pages had, or does
  knowing it's being analyzed introduce a milder version of the same
  problem? Worth sitting with before building.
- Worth prototyping the pitch/pace extraction alone first (no
  classification logic yet) just to see what the raw numbers look like
  day to day, before designing what to do with them.

Nothing here is committed to. Revisit when there's appetite to actually
experiment, not just discuss.
