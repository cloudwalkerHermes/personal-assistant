# Expanding Local Compute for Voicebox (and beyond)

Status: exploratory only, no action taken. Current state is CPU-only
generation on the desktop's Radeon RX 6600 XT — slow but functional.
This doc exists for if/when generation speed becomes enough of a pain
point to justify spending money or real setup time on it.

## Current baseline

- Voicebox's GPU tab only offers a CUDA backend download — CUDA is
  NVIDIA-only, dead end for a Radeon card.
- RX 6600 XT is not on AMD's official ROCm Windows-supported GPU list,
  but it shares the same RDNA2 architecture/instruction set as cards
  that are supported (e.g. RX 6900 XT) — same-architecture compatibility
  suggests it *could* work, possibly needing the common ROCm workaround
  of overriding the GPU version string to identify as a supported
  sibling card. Untested — would be the first, most conservative thing
  to actually try before any of the options below.

## Option A — ASUS UGen300 (external USB accelerator)

- Hailo-10H AI processor, 40 TOPS, 8GB dedicated LPDDR4 (not borrowed
  system RAM), USB-C / USB 3.1 Gen 2 — actual USB3, no Thunderbolt/eGPU
  enclosure needed. ~2.5W draw, plug-and-play. Announced April 2026.
- Claims PyTorch, TensorFlow, and ONNX support, Windows included.
- **Real unknowns**: pricing wasn't confirmed in research — check
  ASUS's product page directly. More importantly, generic PyTorch
  framework support does not mean Voicebox specifically has wired up
  code to route inference through a Hailo NPU — its GPU tab only shows
  a CUDA option today, no NPU/Hailo path visible. Device is also weeks
  old as of this writing, so real-world driver maturity is unproven.

## Option B — ZLUDA (CUDA-on-AMD translation layer)

- Translates unmodified CUDA binaries to run on AMD's ROCm runtime —
  claims 80-95% of native CUDA performance if it works cleanly.
- **Legal gray area**: NVIDIA's CUDA license has explicitly prohibited
  translation layers like this since 2021. AMD informally supported the
  project, then forced a takedown in 2024 over legal exposure. Project
  continues from a rebuilt pre-AMD codebase, but this is genuinely
  contested territory, not a sanctioned tool.
- **Stacks on top of Option A's baseline question, doesn't replace it**:
  ZLUDA sits on top of ROCm — it doesn't help at all unless ROCm itself
  already works on the 6600 XT. Two layers of uncertainty compounding
  (does ROCm work on this card → does ZLUDA cleanly translate whatever
  CUDA calls Voicebox actually makes), plus real manual setup effort
  rather than a toggle.

## Verdict

Nothing here is a clean, confident win. Ranked by realistic effort vs.
payoff:

1. **Try the native ROCm override trick first** — free, just config,
   answers the one question (does this card work at all) that both
   other options depend on or are irrelevant without.
2. **ASUS UGen300** — cleanest hardware story if Voicebox ever adds
   real NPU support, but that support doesn't exist today and pricing
   is unconfirmed. Worth re-checking in a few months as the device
   matures, not an impulse buy now.
3. **ZLUDA** — most fragile of the three: legal gray area, depends on
   Option 1 working anyway, real setup effort. Tinkering project, not
   a reliable upgrade path.

None of this is worth chasing unless CPU-only generation speed actually
becomes a recurring problem in practice — right now it's slow but
functional, which doesn't justify the effort/cost/risk of any of these.
