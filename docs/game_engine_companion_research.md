# AI Game Companion Research — OpenMW & Daggerfall Unity

Status: hobby-tagged, exploratory only, not pursued. Researched
2026-06-19/20.

## The idea

Could Hermes/Arcus interact with or control an actor inside an
open-source classic RPG engine (Morrowind via OpenMW, or Daggerfall
via Daggerfall Unity), via a local bridge?

## OpenMW (Morrowind)

- Real engine, GPL, GitHub. Does **not** include original game assets
  (still requires owning Morrowind's data files).
- Has a genuine Lua scripting API with actor control (`ActorControls`
  — confirmed real, e.g. making NPCs attack/move).
- **No evidence of networking/socket/HTTP access exposed to the Lua
  sandbox.** The only "networking" architecture referenced anywhere is
  a separate, unfinished multiplayer mode — not a general API surface
  scripts can use to talk to an external process.
- Realistic bridge if pursued: **file-based polling**, not a clean API.
  An external script writes a "command" to a file; a Lua script
  attached to an actor polls that file every game tick and acts on it;
  writes a result back to another file for the external process to
  read. Works, but laggy and clunky compared to a real API.
- Verdict: fun tinkering, not a productivity unlock. Doesn't feed
  anything else on the roadmap.

## Daggerfall Unity

- C# DLL-based mod API (DocFX-generated docs at
  thelacus.github.io/daggerfall-unity-docs). The core documented mod
  API itself doesn't expose networking either.
- However, a **community fork** (`EmptyBottleInc/DFU-Tanguy-Multiplayer`
  on GitHub) adds real client-server multiplayer using Unity's Mirror
  networking library — actual netcode, syncing discovered locations and
  dungeon enemies between clients.
- This means a genuine network protocol exists (unlike OpenMW), so in
  principle an AI-controlled "companion" could connect as a second
  client rather than needing file-polling.
- Caveat: it's an unofficial custom fork, not mainline. Community
  reports (Daggerfall Workshop forums) describe building multiplayer
  mods as fighting C# compiler quirks and mod-builder limitations —
  not a stable, documented system to build against.
- To actually plug in, would require building/maintaining a custom
  Unity/C# client against that fork's unofficial netcode — a real
  game-dev side project in a different stack (C#/Unity) than anything
  else built this session (Python).
- Verdict: more architecturally "real" than OpenMW (actual networking
  exists), but a bigger time investment for the same hobby-tier payoff.
  Worth it only as a C#/Unity side project for its own sake.

## Bottom line

Neither is worth prioritizing against anything on the actual roadmap.
OpenMW is the lower-effort, more-limited option (file-polling bridge).
Daggerfall Unity is the higher-effort, more-capable-in-theory option
(real netcode, but an unofficial/finicky fork). Parked as hobby
exploration, not a roadmap commitment.
