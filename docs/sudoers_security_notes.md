# Sudo Access — Current State & Future Considerations

Status: no sudo access exists today (verified 2026-06-19, `sudo -n true` →
"a password is required"). This doc exists for if/when that ever needs
to change, not because it needs to change now.

## Current state is the secure baseline

Every task this session has run fine with zero elevated privileges —
crontab edits, file operations, package installs (`uv pip install`),
systemd status checks (`systemctl is-active`, `journalctl -u`), browser
automation. All of it operates on the user's own files/crontab or reads
system state read-only. No root needed anywhere so far.

This is a feature, not a gap: smaller blast radius if anything ever goes
wrong in a session (bad instruction, prompt injection, a buggy script) —
the damage is capped at what the `arcus` user can already touch, not
the whole machine.

**Don't grant broader access than a concrete need justifies.** If/when
something genuinely requires elevation, the right move is a narrowly
scoped `sudoers.d` rule for that exact need — never blanket
`arcus ALL=(ALL) NOPASSWD: ALL`.

## If a real need shows up, do it like this

A dedicated file under `/etc/sudoers.d/` (e.g. `arcus-hermes`), not an
edit to the main `/etc/sudoers` file — keeps the grant isolated, easy to
review, easy to revoke by deleting one file.

```
# /etc/sudoers.d/arcus-hermes
arcus ALL=(root) NOPASSWD: /usr/bin/systemctl restart cron
```

Rules for whatever goes in that file:

- **Enumerate exact commands with full absolute paths.** No wildcards
  on the binary itself (`/usr/bin/systemctl *` is far broader than
  `/usr/bin/systemctl restart cron`).
- **Never grant a shell-spawning or arbitrarily-scriptable binary** —
  `sudo vim`, `sudo less`, `sudo python3 <anything>`, `sudo find ... -exec`,
  etc. are classic sudoers escapes (see GTFOBins) that turn one
  narrow grant into full root. If a tool can `:!sh` or `!bash` from
  inside it, it doesn't belong in a NOPASSWD rule.
- **NOPASSWD only where automation genuinely requires it.** Cron jobs
  have no TTY to answer an interactive password prompt — so *if* a
  future cron-triggered task ever needs a privileged command, NOPASSWD
  isn't a convenience shortcut there, it's the only way it can work at
  all. That's a real, narrow justification — not a reason to default to
  NOPASSWD everywhere out of laziness.
- **One line per command, not a comma-swept list of "everything Hermes
  might need."** Add lines as concrete needs arise, don't pre-grant for
  hypotheticals.

## Auditability

`sudoers.d` usage is already logged by the system (`journalctl`/auth
log) independent of anything we build. Worth considering, if this ever
becomes real: a `system_health.py`-style check that watches for any
sudo invocation outside the expected allowlist and flags it — same
issues-only philosophy already established for that monitor, just
applied to privilege use instead of cron drift.

## When this might actually come up

No concrete need exists today. Plausible future triggers, if they ever
materialize:
- A system-level package (`apt`) needed by some future script, where
  the user-level `uv pip install` path doesn't apply (system binaries,
  not Python packages).
- Managing a systemd service directly (e.g. restarting `cron` itself if
  it ever needs it, rather than just reading its status as we do now).
- Daedalus-related self-hosted sandbox work, if that ever needs
  container/process management beyond the current user's permissions.

None of these are active asks — just the realistic shapes a future
request might take, so the scoping principle above has something
concrete to apply to when the time comes.
