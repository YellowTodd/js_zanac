---
id: "0010"
status: done
range: 0xE300-0xE71E
strategy: live_debug
budget_turns: 40
---

# Sprint 0010 — Live debug session: 5 priority open questions

## Goal

Answer the five priority open questions from `live-debug.md` using the openMSX
internal debugger with user-assisted gameplay input.

1. **Who sets bit 0 of (0xE700)?** — write-watchpoint → PC capture.
2. **Is 0xE620 a direct name-table shadow?** — memory dump + VRAM compare.
3. **Entity slot live dump (offsets 3–27)** — breakpoint at `entity_dispatch` (0x445F).
4. **Scroll state 0xE704–0xE713** — snapshot diff across scroll cycle.
5. **Base encounter consumer (0xE150 watcher)** — read-watchpoint on 0xE150.

## Inputs

- `kb/data/scroll_state.md` — known scroll_flags and field layout
- `kb/symbols/0x4000-init/entity_dispatch.md` — entry point 0x445F, slot stride 32
- `kb/symbols/0x9000-scroll/scroll_sync.md` — spin-loop context
- `kb/symbols/0x9000-scroll/place_tile_group.md` — writes 0xE150/0xE151/0xE71E
- `kb/symbols/0x9000-scroll/check_col_clear.md` — scans 0xE620

## Verification plan

Each question uses a specific openMSX debug command; results are pasted back
as verification transcripts.

## Summary (filled at end)

All 5 priority questions answered or substantially advanced via live openMSX debug.

**Q1 — Who sets bit 0 of (0xE700)? ANSWERED.**
`SET 0,(IX+0)` at **0x9805** inside `scroll_precompute` (~0x97E3–0x980D). Passive
write-watchpoint over 20 frames captured the full per-frame 0xE700 write sequence:
`RES 1` (0x948A) → `RES 0` (0x97F8) → **`SET 0` (0x9805)** → `SET 1` (0x9809)
→ `RES 0` by ISR (0x9A86). New KB: `scroll_precompute.md`.

**Q2 — Is 0xE620 a direct name-table shadow? ANSWERED (no).**
0xE620 is **entity slot 25** (0xE300 + 25×32). `check_col_clear` scans the type
bytes of entity slots 25→5 (stride -32) treating tile-ID-range values as
occupancy markers. No separate shadow buffer exists. The sprint 0009 hypothesis
was wrong. `check_col_clear.md` updated to `confirmed`; `entity_table.md` end
corrected from 0xE51F → 0xE63F.

**Q3 — Entity slot layout offsets 3–27. SUBSTANTIALLY DECODED.**
Two live dumps (running and paused with structures visible) revealed:
- Bit 7 of type byte = active state flag; bits 0–6 = dispatch type.
- Slots 5–25 are ground-structure slots; types 39, 44, 82 confirmed.
- `+0x1B/+0x1C`: 16-bit LE pointer from type-44 entity to its type-39 column-marker.
- `+0x1D`: column-width counter incremented by `place_tile_group`.
- Player slot fully mapped at offsets 0x01–0x12. `entity_table.md` updated.

**Q4 — Scroll state 0xE704–0xE713. DECODED.**
Two snapshots (paused vs mid-gameplay) plus disassembly of 0x97D9 and 0x9493:
- 0xE701: `stage_index` (stable 0x01 = Round 1). **Corrects sprint 0008 which
  wrongly placed this at 0xE702.**
- 0xE702: `level_row_ctr` — increments by 1 per scroll row.
- 0xE704–0xE705: tile-stream ROM pointer. 0xE706–0xE707: current stream value.
- 0xE710: `current_scroll_speed`; 0xE712: `target_scroll_speed`; both 0x34 = full speed.
- 0xE711: timing accumulator (changes per frame); 0xE713: mod-4 velocity timer.
`scroll_state.md` fully rewritten with new confidence levels.

**Q5 — Base encounter consumer of 0xE150. IDENTIFIED.**
Read-watchpoints did not fire (openMSX limitation). Static source search found
exactly 2 readers of 0xE150: `scroll_velocity_ctrl` (0x9480) and `base_encounter_ctrl`
(0xBFCB). Neither spawns projectiles directly. The actual base-projectile dispatch
uses 0xE71E (the attack-list pointer) via the entity handler near 0xBFA0 — which
uses `(IX+0x25)` confirming it is processed by entity_dispatch. New KB:
`scroll_velocity_ctrl.md`, `base_encounter_ctrl.md`.

**New KB files:** `scroll_precompute.md`, `scroll_velocity_ctrl.md`, `base_encounter_ctrl.md`.
**Updated KB files:** `check_col_clear.md`, `scroll_state.md`, `entity_table.md`.

**Still uncertain:**
- 0xE704–0xE707 stream pointer/value full semantics.
- Base entity type ID (entity dispatched from 0xBFA0 area; type not yet read).
- 0xE71E consumer: the actual base-projectile spawner.
- Entity slot offsets +0x0C–0x1A for types 1, 44 (partially observed, not decoded).
- 0xE711 timing accumulator and 0xE70F stable value purposes.

**Next sprint candidates:**
- **0011 — Base entity handler**: Read entity type at jump-table offset for 0xBFA0
  handler; trace 0xE71E reader to confirm projectile spawn path.
- **0012 — Entity type survey (types 39, 44, 82, and others)**: Read jump-table
  entries and stub-decode each ground-structure handler to map all active types.
- **0013 — Scroll velocity ramp**: Trace what sets 0xE712 to 0 when approaching
  a base; confirm the deceleration mechanism.
