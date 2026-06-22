# Voicebox — Shared Voice API for the Agent Network

For any Claude/agent instance on Mike's home LAN (desktop/Hermes, Pi 4B/Kalshi,
N150/Aether — all behind the same router). Voicebox runs on the Windows
desktop and is reachable over plain HTTP from any machine on the network.
No VPN, no tunnel, no special setup needed beyond what's below.

## Where it lives

```
http://192.168.1.3:17493
```

**Caveat**: this is the desktop's current LAN IP via DHCP — it *can* change
after a router reset or long power outage. If this address stops responding
and the machine is definitely on, re-check the IP on the desktop
(`ipconfig` on Windows) rather than assuming the service is down. A DHCP
reservation on the router would make this permanent if it becomes a problem.

## Auth

**None.** No API key, no token, no header required. This is a deliberate
tradeoff accepted because it's a private home LAN with only trusted
machines on it — every other Claude instance using this should know there's
no credential gate, just network reachability.

## Quick verify

```bash
curl -s -m 5 -o /dev/null -w "HTTP %{http_code}\n" http://192.168.1.3:17493/
```
`200` = reachable. `000`/timeout = check the IP, check the machine's awake,
or check Windows Firewall/network profile on the desktop side (see Gotchas).

## Full live API schema

```bash
curl -s http://192.168.1.3:17493/openapi.json
```
Always check this directly rather than trusting this doc to stay current —
it's the live ground truth for every endpoint and field.

## Verified working calls (this session)

**Generate speech (async — poll for completion):**
```bash
curl -X POST http://192.168.1.3:17493/speak \
  -H "Content-Type: application/json" \
  -d '{"text": "your text here", "profile": "<profile-id-or-name>"}'
```
Returns immediately with `status: "generating"` and a generation `id`.
Poll `GET /history/{id}` until `status: "completed"`.

**`/speak` requires either `profile` or a configured default** — `engine`
alone is not enough, even though it's a separate field in the schema. If
you get `"No voice profile resolved"`, you need an actual profile object
(see below) or to set a default in Voicebox's Settings → MCP panel.

**List existing voice profiles:**
```bash
curl http://192.168.1.3:17493/profiles
```
Check this first — a profile named "Agent Smith" already exists (created
this session). Don't recreate it; reuse its `id`.

**Create a profile (preset voice, no cloning):**
```bash
curl -X POST http://192.168.1.3:17493/profiles \
  -H "Content-Type: application/json" \
  -d '{"name": "...", "voice_type": "preset", "preset_engine": "kokoro", "preset_voice_id": "am_michael", "default_engine": "kokoro"}'
```
List available presets per engine first: `GET /profiles/presets/{engine}`.

**Transcribe audio (Whisper, runs locally):**
```bash
curl -X POST http://192.168.1.3:17493/transcribe \
  -F "file=@/path/to/audio.wav"
```

## Gotchas learned the hard way this session

- **Kokoro is preset-only — it does not clone from samples.** For actual
  voice cloning, the profile's engine needs to be `qwen` (Qwen3-TTS),
  `chatterbox`, `chatterbox_turbo`, `luxtts`, or `tada`. A profile can have
  samples attached and still just use a generic preset voice if its engine
  is set to `kokoro` — check `default_engine` on the profile, not just
  whether `sample_count > 0`.
- **Sample audio has a quietness floor.** Mean volume around -43 dB got
  rejected as "too quiet." Normalize first:
  `ffmpeg -i in.mp3 -af "loudnorm=I=-16:TP=-1.5:LRA=11" out.mp3` — targets
  -16 LUFS, which cleared the check.
- **Samples have a ~30 second max** (per Voicebox's own UI constraint).
- **Reachability required two fixes on the Windows desktop side**, neither
  obviously connected to Voicebox itself:
  1. Voicebox's own "Allow network access" setting (off by default — binds
     to loopback only until enabled) + an app restart to actually take effect.
  2. The desktop's Ethernet connection was classified "Public" by Windows,
     not "Private" — even after approving the Windows Firewall prompt for
     "Private networks," traffic was still dropped because the underlying
     connection wasn't actually on that profile. Fixed via Settings →
     Network & Internet → Ethernet → toggle to Private. If a similar
     "reachable from my machine but nothing else" symptom shows up, check
     this on the desktop before assuming it's something on the calling
     machine's end.

## What this unlocks

One shared local voice backend (TTS, voice cloning, transcription) for the
whole agent network instead of each machine needing its own setup or its
own ElevenLabs API cost. Confirmed working end-to-end: REST call → audio
generated → played through the desktop's actual speakers.
