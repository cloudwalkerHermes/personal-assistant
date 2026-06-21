# Voicebox — Local Voice Stack Research

Status: researched 2026-06-21, **not installed**, candidate for future
evaluation. Surfaced via a YouTube video, verified against the actual
repo before trusting the video's claims.

## What it is

`jamiepine/voicebox` on GitHub — open-source, local-first AI voice
studio. Free/unlimited alternative to ElevenLabs (and to Whisper-based
dictation setups). MIT licensed.

## Credibility check

- 31.6k GitHub stars, 588 commits on main, actively maintained — v0.5.0
  shipped April 2026.
- Built by Jamie Pine (also behind Spacedrive) — established developer,
  not a fly-by-night project.

## Platform/hardware fit (the question that actually decides this)

- **Linux supported (build-from-source) + Docker** — viable on this
  WSL2/Debian box, contrary to the video's Windows/Mac-only framing.
- CPU fallback available everywhere — works without a dedicated GPU,
  just slower. Acceleration backends exist for CUDA/ROCm/DirectML/Intel
  Arc if hardware is available later.

## What it exposes

- **REST API** — generation, transcription, profile management.
- **Built-in MCP server** (HTTP or stdio transport), four tools:
  `voicebox.speak`, `voicebox.transcribe`, `voicebox.list_captures`,
  `voicebox.list_profiles`.
- Voice cloning from a few seconds of reference audio, 7 TTS engines,
  23 languages, system-wide dictation via global hotkey, multi-voice
  timeline editor.

## Roadmap intersection — why this matters more than "a cool tool"

This isn't an isolated find — it overlaps directly with three existing
items, all in `project_personal_assistant.md`:

| Roadmap item | Status | How Voicebox changes it |
|---|---|---|
| 4 — ElevenLabs TTS integration | ✅ Built | `voicebox.speak` is a free, unlimited, local drop-in replacement — removes the per-character ElevenLabs API cost entirely. |
| 11 — Telegram voice dictation → Whisper → GCal | 🔲 Not built | `voicebox.transcribe` does the job the separate Whisper integration was meant to do — one tool instead of two. |
| 15 — Google Maps + Arcus voice clone | 🔲 Not built | Voice cloning is exactly the mechanism that item was waiting on (was listed as "ElevenLabs voice clone, Waze pack, or custom Android TTS"). |

Potential outcome if adopted: collapses three separate future/ongoing
costs and builds into one local install, and removes a recurring API
bill at the same time.

## Open questions before adopting

- Actual voice quality/latency on this specific hardware (CPU-only
  unless a GPU is added) — untested.
- Whether the MCP server integrates cleanly with the existing
  Telegram-based architecture, or whether it'd need its own bridge
  script (same shape as everything else built so far).
- Migration cost of moving `wellness_check.py` off ElevenLabs onto
  Voicebox's API once evaluated.

Not installed. Worth a real hands-on evaluation when there's bandwidth,
given the three-item overlap above.
