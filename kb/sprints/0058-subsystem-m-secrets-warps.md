---
id: "0058"
status: done
range: 0x43D2-0x43D9,0x425A-0x425A,0x8A05-0x8A13,0x945C-0x945C
strategy: cross_cutting_slice
budget_turns: 15
subsystems: [M]
---

# Sprint 0058 — Subsystem M (Secrets & warps): closing slice

> **Subsystem slice:** [[M-secrets-and-warps]] — takes M from stub (~15%) to done.
> M owns no code of its own; this slice ties together the already-documented
> routines in J/K/E/D that expose the ESC-continue and the round-0 stage, adds a
> live warp confirmation, and closes the stub's three open questions.

## Goal

1. Establish the exact mechanism of the title-screen **ESC-continue** and which
   RAM byte it controls (`E701`).
2. Determine what the "secret round 0" actually is (playable stage vs. debug map
   vs. the ending) and confirm it live.
3. Resolve whether any **in-game** warp trigger (a "warp orb") exists beyond the
   title path, and whether any **hidden key combo** forces a round.

## Method

- Static: traced every `E701`/`E722` writer in `source/zanac.asm`
  (`E701`: 0x403F, 0x9439; `E722`: 0x8A0B base core, 0x91F4 script jump, 0x92B2
  ending) and every gameplay `SNSMAT` call (0x4366/0x438B/0x4396/0x43D4/0x4DAA/
  0x4E1B — all title/ESC/pause, none in-gameplay).
- Live: `tools/sprint0058_verify.py` — ROM-read `stage_stream_ptr_table[8]`, then
  a one-shot bp at 0x425A forcing `E701 = 0`, SPACE to start, screenshot.

## Findings

- **ESC-continue** is the only secret *input*: `title_screen_init` resets
  `E701 = 1` only when ESC is **not** held (`check_esc_key` 0x43D2); ESC held
  retains `E701`. Cold boot has `E701 = 1`, so continue matters only after a round
  was advanced in the same power cycle.
- **Round 0 is a real playable stage** (stream 0xA65C), *not* a debug map. Live
  warp shows red/blue-striped terrain, a "ROUND 0" banner, HUD "ROUND 0 / LEVEL
  0", ship + base. The **ending** is a later segment (0xA6F4) of the *same* stream
  with the ZANAC-logo tiles + credits flag ([[ending_setup]]).
- **`E701 = 0` in unmodified play** arises only from the round-8 → ending
  transition (`resolve_round_from_ptr` maps sub-round-1 pointers → 0). Continue
  can then re-enter round 0. No **second loop**.
- **No hidden key combo** exists (all `SNSMAT` reads catalogued). The base-core
  `+0x1C/1D` → `E722` path is the general round-advance mechanism and *could*
  data-drive a mid-game round-0 warp, but no shipped spawn record is known to do
  so — the "warp orb / idol base" wording was folklore; corrected in
  `keyboard-input`.

## KB changes

- `kb/subsystems/M-secrets-and-warps.md` — rewritten, `coverage: done`,
  `status: done`.
- `kb/guides/keyboard-input.md` — corrected the "warp orb released by an idol
  base" claim to the actual base-core `+0x1C/1D` mechanism (unconfirmed in data).
- `tools/sprint0058_verify.py` — new; `/tmp/round0.png` reference shot.

## Summary (filled at end)

M closed. The subsystem is thin and fully cross-referential: ESC-continue
(`check_esc_key`/`title_screen_init`, retains `E701`), round 0 = the playable
stream 0xA65C whose tail is the ending, round-advance via `E722` →
`resolve_round_from_ptr` → `E701`, and `scripts/warp.tcl` as the debug entry.
No hidden key combos; no observed in-game warp entity. Live-confirmed.
