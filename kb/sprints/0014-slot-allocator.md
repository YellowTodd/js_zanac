---
id: "0014"
status: done
range: 0x4496-0x44A5
strategy: callgraph_leaf
budget_turns: 5
---

# Sprint 0014 — Entity slot allocator

## Goal
Decode `sub_4496` (0x4496), the free-slot allocator called by `spawn_col_marker`
and entity handlers.

## Inputs
- `kb/data/entity_jump_table.md` — callers
- openMSX disasm

## Summary

Six instructions. Scans entity slots 5–25 (the ground-structure pool,
0xE3A0–0xE620) for the first slot whose type byte is 0 (inactive). Returns
HL = that slot's base address with carry clear. If all 21 slots are occupied,
returns with carry set.

**Confirms:** slots 0–4 are never touched by this allocator — they are
permanently reserved for the player and player-managed entities (bullets etc.).
