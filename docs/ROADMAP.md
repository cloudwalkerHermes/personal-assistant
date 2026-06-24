# Personal Assistant / Arcus — Full Roadmap

Last updated: 2026-06-24. Consolidated for handoff — full status of every
item discussed, with pointers to detailed docs where they exist.

## Live cron schedule

| Time | Script | Output |
|---|---|---|
| 06:00 daily | `tasks/shipped_yesterday.py` | Telegram (System Health channel) + logs/shipped_yesterday.log |
| 07:00 M/W/F | `tasks/money_status.py` | Telegram + logs/money_status.log |
| 07:05 daily | `tasks/garmin_morning.py` | Telegram + logs/garmin_morning.log |
| 07:15 daily | `tasks/wellness_forecast.py` | Telegram + logs/wellness_forecast.log |
| 07:20 Wed | `tasks/weekly_ads.py` | Telegram + logs/weekly_ads.log |
| ~~07:25 Wed~~ | ~~`tasks/aldi_ads.py`~~ | **paused** — commented out in crontab, see item 3 |
| 07:00 Jun15/Dec15 | `scripts/scrape_kroger_history.py` | logs/kroger_history.log |
| 0/4/8/12/16/20:24 | `tasks/system_health.py` | Telegram (System Health channel), issues-only watchdog |
| 13:00 daily | `tasks/wellness_check.py` | Voicebox local playback (Rory Cochrane), Telegram text fallback only if Voicebox unreachable |
| 06:30 daily | `cmd.exe start firefox <youtube link>` | logs/morning_video.log |
| 06:40 daily | `cmd.exe start firefox <yahoo fantasy>` | logs/fantasy_baseball.log |
| 06:40 daily | `tasks/shipped_yesterday.py` | (listed above) |
| 7/11/15/19:00 daily | `tasks/rory_checkin.py` | Voicebox local playback, personal/private, excluded from watchdog |

## Integrations

- **Plaid** (Production): Capital One + U.S. Bank, transactions in `personal-assistant.db`
- **Google Calendar**: OAuth token at `token.json`, "Bills & Recurring" calendar
- **Garmin Connect**: OAuth tokens at `.garmin_tokens/`
- **Kroger**: client credentials in `.env`, sale dedup via `sale_alerts_sent`
- **Telegram**: shared sender at `integrations/telegram.py`. Main channel `-1003940070749`. System Health channel `-1004460746660` ("System Health Cloudwalker Enterprises", Arcus + Kalshi bots both admins).
- **Voicebox**: `192.168.1.3:17493`, no auth, LAN-reachable from any machine on the same router (Arcus desktop, Kalshi/Pi 4B, Aether/N150). Full setup notes: `docs/voicebox_network_access.md`.

## Roadmap items

1. ✅ **Garmin trending** — `garmin_daily` table, 7-day arrows in morning report. Garmin's own fitness-age feature removed entirely (2026-06-18) — broken from day one, called a nonexistent method; also rejected on principle (unrealistic BMI target).
2. ✅ **Wellness forecast + check-in** — `wellness_forecast.py` (7:15am) + `wellness_check.py` (1pm conditional). Composite score: `(sleep%9h + sleep_score + battery_waking + RHR×0.5) / 3.5`. Voice check-in migrated 2026-06-22 from ElevenLabs/Callum to Voicebox/Rory Cochrane, local desktop playback only (Telegram voice delivery dropped for now).
3. ⏸️ **Aldi ad scraper** — paused 2026-06-24. Cause unrelated to the scraper itself: a separate, temporary Aldi Blind Box giveaway cron had broken countdown UX and a bad outcome at checkout. Script intact, cron commented out, not deleted. **Don't re-enable without Mike bringing it up first.**
4. ✅ **ElevenLabs → Voicebox migration** — superseded 2026-06-22. No ElevenLabs usage remains in the codebase. Voicebox hosts working clones: Hugo Weaving (Agent Smith), Rory Cochrane, and others created directly through Voicebox's own UI outside this codebase (Leonard Nimoy, Captain Kirk, James Cagney, Michael Caine, Cathy Moriarty, others).
5. 🔲 **Telegram Rich Messages** — `sendRichMessage` API rejected all payload shapes tried; builders left in `integrations/telegram.py` for if the API ever stabilizes. Not pursued further.
6. ✅ **Transaction categorization** — `money_status.py` buckets variable spend by Plaid category instead of one flat number.
7. ✅ **Kroger purchase history scraper** — `scripts/scrape_kroger_history.py`, biannual cron (Jun15/Dec15).
8. 🔲 **Low balance alert** — designed to live inside `system_health.py` as another threshold check (same issues-only pattern), not yet built.
9. ⏳ **Yahoo Fantasy Baseball** — OAuth API access pending/applied for. Interim stopgap: 6:40am cron just opens the Yahoo Fantasy tab as a manual-lineup-setting reminder.
10. 🔲 **Google Maps/OAuth investigation** — not started.
11. 🔲 **Telegram voice dictation → transcription → GCal** — not built as originally scoped (separate Whisper integration); likely superseded in practice by Voicebox's own dictation feature + `/transcribe` endpoint, which already does this locally.
12. 🔲 **Android Auto investigation** — not started.
13. 🚫 **GCal nudge/rescheduling** — shelved.
14. 🔲 **Quality of life additions** — gas alerts, weather-aware calendar, prescription refill reminders, sleep debt tracker, bill paid confirmation. Not started.
15. ✅ **Arcus voice clone** — done via Voicebox (item 4), sitting on Hugo Weaving/Rory Cochrane rather than a from-scratch ElevenLabs clone. Google Maps/navigation integration piece not started.
16. 🔲 **Arcus memory system** — two-way NL knowledge store (STORE/RECALL/UPDATE/DELETE via plain English). Blocked on a separate Claude API key (distinct from Claude Code subscription). Not built.
17. 🔲 **Health-ranked ad sorting** — Open Food Facts (OFF) API approach designed (Nutri-Score + NOVA group composite), not built. Intended as a first real use case for item 16's query layer, not a standalone script.
18. 📋 **Household/Life Backlog** — fully designed, not built. Markdown + YAML frontmatter, real folder hierarchy, Telegram creation/updates, two-way Google Tasks sync. Full spec: `docs/household_backlog_spec.md`.
19. 📋 **Sudoers/security hardening** — notes only, no active need. Currently zero sudo access (confirmed, this is the secure baseline). Full notes: `docs/sudoers_security_notes.md`.
20. 🎮 **[HOBBY] AI game companion research** — OpenMW/Daggerfall Unity, not pursued. Full notes: `docs/game_engine_companion_research.md`.
21. ✅ **Voicebox** — LIVE. Local voice stack (`jamiepine/voicebox`), LAN-reachable, REST API confirmed working end-to-end. CPU-only generation (slow but functional). Full setup/gotchas: `docs/voicebox_network_access.md`.
22. 📋 **Local compute expansion** — exploratory, no action taken. ASUS UGen300 (USB NPU accelerator) and ZLUDA (CUDA-on-ROCm translation layer) researched; neither a confident win. Full notes: `docs/local_compute_expansion.md`.
23. 💭 **Holistic wellness tracker** — pure ideation. Combining a dedicated voice check-in's prosody (pitch/pace) with Garmin stress score to calibrate `wellness_check.py`'s tone. Full notes: `docs/holistic_wellness_tracker.md`.
24. 💭 **Agent radio show** — pure ideation. Shared Telegram "radio station," one bot as scheduler, every agent gets a Voicebox persona and a broadcast slot. Likely waits for Daedalus (cross-machine scheduling is its job, not worth hand-rolling early). Full notes: `docs/agent_radio_show.md`.

## Status key

✅ done · ⏸️ paused (intentional) · 🔲 not started · ⏳ blocked/waiting · 🚫 shelved · 📋 designed, not built · 💭 ideation only · 🎮 hobby, not a real priority
