---
id: "0045"
status: done
range: 0x9444-0x945B,0x945C-0x946D,0xE102,0xE110,0xE701
strategy: subsystem_slice
budget_turns: 26
subsystems: [K]
---

# Sprint 0045 — Subsystem K (Game-Flow State Machine): confirm flag map + rounds

## Goal

Take subsystem K to fully documented (all `confirmed`). The four K routines were
already confirmed; the open gaps were (a) the E102/E100 flag-bit map "partial"
and (b) round-progression / loop-after-final-round not traced. Close both, and
upgrade `game_state_block` from `likely`.

## Inputs

- `kb/subsystems/K-game-flow-state-machine.md`
- `kb/symbols/0x4000-init/{main_game_loop,level_complete_handler,game_over_handler,wait_fire_or_timeout}.md`
- `kb/data/game_state_block.md`, `kb/guides/input-state-machine.md`
- Source: `resolve_round_from_ptr` 0x9444, table 0x945C, level_complete 0x40DA.
- Tools: warp (`arm_warp`) + `savestates/game-end.oms` (round-8 boss kill).

## Verification plan

`tools/sprint0045_verify.py` — Phase A `ZanacGame` (warp + injection + microexec),
Phase B `ShotSession` (`-savestate game-end.oms`). Per the task, rounds were not
played to completion; progression was confirmed via the round resolver + the
end-state savestate.

## Summary (filled at end)

**All 14 checks passed; subsystem K → fully documented ✓.**

### Key corrections / findings

- **Round lives in `E701`, not `E110`.** Warp to r1/r3/r8 → `E701` = 1/3/8 while
  `E110` stayed `0x01`. `game_state_block`'s "E110 = round (1–8)" was wrong; E110
  is a shot-state byte (set at 0x7684). Corrected; round documented in `E701`.
- **E102 flag map** was already fully enumerated + confirmed in
  `input-state-machine` (sprint 0032); propagated into `game_state_block` and
  reconciled bit 7 = `go_to_title` (not "game running").
- **Round progression** (new guide `round-progression.md`): scroll engine puts
  the next round's stream pointer in `E722` + sets E102 bit 5;
  `level_complete_handler` calls **`resolve_round_from_ptr`** (0x9444) to map
  `E722` → round → `E701`. After round 8 the engine sets `E722 = 0xA6F4` + bits
  5+3; the resolver maps it to `E701 = 0`, bit 5 clears, bit 3 fires credits →
  title. **No second loop.**

### Live confirmation

| Check | Result |
|-------|--------|
| `E701` = warp round (1/3/8) | pass; `E110` constant 0x01 |
| game-over: set E102 bit 1 | `game_over_handler` set bit 7 (E102=0x82), wrote " GAME OVER " to VRAM 0x3987 |
| `resolve_round_from_ptr` microexec | all 8 table entries → rounds 8..1; 0xA6F4 → 0 |
| end savestate at load | E102=0x28 (bits 5+3), E701=8, E722=0xA6F4 |
| end savestate after ~4 s | E701→0, E102=0x08 (bit 5 cleared, bit 3 credits) |

### New symbols / data

- `resolve_round_from_ptr` (0x9444, routine) — source label renamed from
  `SUB_ram_9444`; 2 call-site comments updated.
- `stage_stream_ptr_table` (0x945C, data) — source label added; 9 LE pointers,
  entry *i* = round `8−i`, 9th = ending stream.
- `round-progression.md` (guide).
- `redisasm verify` byte-identical after both source edits.

### Files

- `game_state_block.md` → `confirmed`; E102 expanded, E110 corrected, notes added.
- `level_complete_handler.md` — round-advance section + `resolve_round_from_ptr`.
- `K-game-flow-state-machine.md` — coverage `done`, state table fixed, gaps cleared.
- `CLAUDE.md` coverage table K → done ✓.
- `tools/sprint0045_verify.py`.

`zanackb validate` 0 errors. `redisasm verify` byte-identical.
