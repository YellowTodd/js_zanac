---
address: 0xBFD6
end: 0xBFFA
kind: routine
name: base_encounter_ctrl
confidence: confirmed
inputs: {}
outputs: {}
clobbers: [AF, HL]
calls:   [0x5C25, 0x0053, 0x4C74, 0x42F8]
called_by: [0x415d, 0xbfb9, 0xbfc6, 0xbfd3]
tags: [base, gamestate, vdp]
sprint: "0052"
---

# base_encounter_ctrl

## Summary

> **Name correction (0052):** despite the name this is **not** the base
> open/close/fire controller — it is the encounter-counter **HUD readout**
> (renders 0xe12e/0xe132/0xe130 as hex to the name table via `render_hex_byte`).
> The actual base encounter is driven by the bfab–bfd0 counters plus the
> 0xe150/0xe102 flags set by [[handler_type72_base_core]] and
> [[handler_type73_base_segment]].

Shared **display tail** entered by fall-through from the base-encounter counter
mutators ([[inc_encounter_inner]] 0xBFCB, [[dec_encounter_inner]] 0xBFC2, and
`SUB_bfc8` 0xBFC8). After a counter (0xE12E / 0xE130) changes, this writes the
updated counter values to the VRAM name table via BIOS WRTVRM (0x0053) —
the base-encounter HUD readout — and re-enables the VDP interrupt.

The counter logic that precedes this tail moved to its own files in sprint 0029
([[inc_encounter_a]], [[dec_encounter_a]], [[dec_encounter_b]],
[[inc_encounter_inner]], [[dec_encounter_inner]]). `SUB_bfc8` (0xBFC8) is the
boss-gated increment variant for 0xE130 (loads HL=0xE130, falls into 0xBFCB).

## Analysis

Source lines 7617–7647.

```
; ── Shared display tail (BFD6) ──
BFD6  LD HL, 0x3839
BFD8  CALL 0x5C25          ; compute VDP address / prepare write
BFDF  LD HL, 0x3859
BFE2  CALL 0x0053          ; BIOS WRTVRM → write to VRAM 0x3859
BFE5  LD A, (0xE12E) ; CALL 0x4C74  ; write digit/value to VDP
BFEB  LD A, (0xE132) ; CALL 0x4C74
BFF1  LD A, (0xE130) ; CALL 0x4C74
BFF4  JP 0x42F8             ; vdp_int_enable
```

### Callers

| Entry | Caller | Purpose |
|---|---|---|
| 0xBFCB | 0xBFAB (SUB_ram_bfab) | Increment 0xE12E, set bit 0 of 0xE12D |
| 0xBFC2 | 0xBFB3 (SUB_ram_bfb3) | Decrement 0xE12E, set bit 0 of 0xE12D |
| 0xBFBF | direct | Decrement/check 0xE130 |

### base_encounter_flags (0xE150) bit usage

- **Bit 0**: base encounter active (set by `place_tile_group` at 0x9380).
  Used by `scroll_velocity_ctrl` (0x9480) to bypass velocity ramp.
- **Bit 1**: **base-active gate** (confirmed 0052). Base segments
  [[handler_type73_base_segment]] (73–79) only activate once 0xe150 bit 1 is set
  (after the segment has scrolled into place via 0xe700 bit 1).

## Notes

- 0xE12E, 0xE130, 0xE132 are in the player entity area (0xE100+). Their exact
  semantics are not yet decoded; they drive a VRAM write to rows 1–2, col 25 of
  the Screen 1 name table (0x3839, 0x3859), consistent with a weapon-level or
  base-health HUD indicator.
- This is NOT the base projectile spawner. The actual projectile spawn path
  reads the attack-list at (0xE71E) and uses entity slots, not 0xE150 directly.
  The spawner is in the base entity handler (observed at 0xBFA0 area, using
  `IX` = entity slot pointer and `(IX+0x25)` for a slot state flag).

## Corrections (2026-07-30)

- **It has callers.** [[level_complete_handler]] calls it unconditionally at
  **0x415D** on every round transition, and its `JP 0x42F8` tail is the only
  thing that re-enables the VDP interrupt before that routine returns.
- **`end` was short.** The last instruction is the `JP 0x42F8` at 0xBFF8, so
  the routine runs to **0xBFFA**.
- **0x0053 is SETWRT**, not WRTVRM (that is 0x004D).
- **There is an inline string.** 0x5C25 is `vdp_set_addr_write`: disable the
  VDP interrupt, SETWRT(HL), then print the NUL-terminated string that follows
  the `CALL`. The bytes at 0xBFDC-0xBFDF are `41 4C 43 00` = **"ALC"**, which
  `source/zanac.asm` currently mis-renders as `LD B,C / LD C,H / LD B,E / NOP`.
  So this routine prints the literal text **ALC** at name-table 0x3839 and the
  hex of 0xE12E / 0xE132 / 0xE130 at 0x3859 - a **live on-screen ALC debug
  readout left in the shipped ROM**, in the status panel at column 25, rows
  1-2. See [[alc-adaptive-difficulty]].
