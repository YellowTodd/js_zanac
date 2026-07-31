---
id: "0041"
status: done
range: 0x43D2-0x43D9,0x424C-0x425C
strategy: subsystem_slice
budget_turns: 20
subsystems: [J]
---

# Sprint 0041 — Subsystem J (Title Screen): confirm all routines

## Goal

Take subsystem J to fully documented. Five of its six routines were already
`confirmed`; the last `hypothesis` was `check_start_key` (0x43D2). Confirm it
with a live trace and fix the stale "SPACE" claim.

## Inputs

- `kb/subsystems/J-title-screen.md`
- `kb/symbols/0x4000-init/{check_start_key,title_screen_init,clear_title_state,display_timer_countdown}.md`
- `kb/symbols/0x5000-gameplay/{title_intro_seq,load_logo_tiles}.md`
- `kb/guides/keyboard-input.md` (E100 layout, row 7 = ESC)
- Source: 0x43D2–0x43D9 (the routine), 0x424C–0x425C (the title_screen_init branch)

## Summary (filled at end)

**`check_start_key` was misnamed and mis-described — it reads ESC, not SPACE.**
Renamed to **`check_esc_key`** (KB file, source label `check_esc_key:`, both
call-site comments). The routine is `LD A,7 / CALL SNSMAT / BIT 2,A / RET`:
returns `Z=1` when ESC (row 7 bit 2) is held.

### Live confirmation (openMSX)

- **Key mapping** (`tools/trace_check_esc.py` keymatrix probe at idle title):
  `keymatrix` row 7 = `0xFF` with nothing pressed, `0xFB` (bit 2 clear) with ESC
  down → **ESC = row 7 bit 2**, the input the routine reads via SNSMAT.
- A boot-time breakpoint on the routine's `BIT 2,A` returns an *unsettled* SNSMAT
  value (the keyboard port isn't stable that early in boot), so the idle keymatrix
  probe is the authoritative check; the routine's instructions are ROM-verified.

### Branch corrected (`title_screen_init`, 0x424C–0x425C)

`CALL check_esc_key` → `PUSH AF` (save Z) → `CALL init_screen_mode` → `POP AF`
→ `JR Z,0x425A`. ESC **not** held (Z=0) → `LD (IX+1),1` sets **E701 = 1** (round
1). ESC held (Z=1) → skip the write → E701 retained → **continue from last round**
(secret round 0 if a warp death left E701=0). `A = 8 − E701` indexes the level
table; `scripts/warp.tcl` patches E701 at 0x425A. (The old entry's "Z=1 if SPACE
pressed / sets E701 if SPACE" wording was wrong on both the key and the polarity.)

### Files

- Renamed `check_start_key.md` → `check_esc_key.md` (now `confirmed`).
- Rewrote `title_screen_init.md` step 7–10 + output/notes (SPACE → ESC, correct polarity).
- Name swap `check_start_key` → `check_esc_key` across active KB (credits_display,
  J/M subsystems, keyboard-input / input-state-machine / openmsx-control / db-sections
  guides). Source label + 2 caller comments updated; `redisasm verify` byte-identical.
- The other five J routines (`display_timer_countdown`, `clear_title_state`,
  `title_screen_init`, `title_intro_seq`, `load_logo_tiles`) were already
  `confirmed` and re-reviewed — no changes needed.

**Subsystem J → fully documented ✓.** `zanackb validate` 0 errors.
