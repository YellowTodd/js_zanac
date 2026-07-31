---
id: "0059"
status: done
range: 0x87AB-0x8947,0x8983-0x8A15,0x9444-0x945B,0xE720-0xE720
strategy: mechanism_decode
budget_turns: 25
subsystems: [M, G]
---

# Sprint 0059 — Idol / orb / warp mechanic

> **Subsystem slice:** [[M-secrets-and-warps]] (+ [[G-enemy-and-spawn-system]]).
> Reverse-engineers the in-game **warp orb** feature that sprint 0058 wrongly
> dismissed as folklore, and catalogues the per-round warp destinations.

## Goal

Decode the "idol → orb → kill-all/warp" mechanic: identify the entities, the
state machine, the data source for warp destinations, and catalogue which rounds
have warp idols and where they send the player. Map the release conditions.

## Findings (all live-confirmed)

- **Idol** = wide ground-structure ([[handler_type70_wide_structure]], types
  70–71/81–82/87–89): shot via the box hit-sub (0x7904), HP in `+0x19`.
- **Orb** = type 72 ([[handler_type72_base_core]], 0x8983): large-circle sprite,
  floats up, `+0x1E` = yellow→black timer (init 4).
- **Effect on player touch** (collision 0x44B0 vs player slot):
  `+0x1E != 0` (yellow) → `explode_enemies` (kill all); `+0x1E == 0` (black) →
  `E722 = +0x1C/1D`, set `E102` bit 5 → `level_complete_handler` →
  `resolve_round_from_ptr` → warp.
- **Destination source**: idol reads `(0xE720)[(IX+0x03)] → +0x1C/1D`; 0xE720 is
  the per-round idol table, set by map-script **cmd 8** ([[level_script_format]]).
- **Per-round warp catalogue** (live E720 read, all 9 rounds): warp idols in
  rounds 1/2/5/7; **R2→R1** and **R5→R4** are backward warps to *earlier* rounds;
  some sub-types randomise `+0x1C` → round 0. Full table in [[idol-warp-orbs]].
- **Correction**: type 72 is the orb, not a "base core that advances rounds";
  the bit-5 path is the warp.

## Verification

- `tools/sprint0059_verify.py` — micro-exec orb effect tail (black→E722 write +
  bit5; yellow→no write) and E722→E701 warp (round 1 → round 5). ✓
- `tools/sprint0059_e720.py` — warp each round, live-read 0xE720, decode header
  stream pointers. ✓

## KB changes

- New guide `kb/guides/idol-warp-orbs.md` (mechanic + catalogue + conditions).
- `handler_type72_base_core.md` — retitled/corrected to the orb (kill-all/warp).
- `handler_type70_wide_structure.md` — idol + warp-destination read documented.
- `scroll_state.md` — 0xE720 renamed `idol_table_ptr`, warp role, confidence
  confirmed.
- `M-secrets-and-warps.md`, `keyboard-input.md` — warp orb reinstated (was wrongly
  called folklore in 0058).

## Summary (filled at end)

The in-game warp is real and fully mapped. Shoot a ground idol → it releases a
type-72 orb → yellow orb = smart-bomb (kill all enemies), black orb = warp to the
round encoded in the per-round idol table (0xE720, via map-script cmd 8). Warp
idols exist in rounds 1/2/5/7 with destinations incl. backward jumps (R2→R1,
R5→R4) and random→round-0. Mechanism live-confirmed end-to-end; the exact
idol-count/position census per round remains open (needs the ground-structure
placement-stream decode). Sprint 0058's "no in-game warp entity" claim is
retracted.
