---
id: "0024"
status: done
range: 0x4912,0x84D1
strategy: live_debug
budget_turns: 8
---

# Sprint 0024 — Animation table confirmation (entity_update bit2)

## Goal

Sprint 0021 decoded the `entity_update` bit2 animation path (routine at 0x4912):
it reads +0x0D/+0x0E as tick counters, +0x0F/+0x10 as frame index/max, and
+0x11:+0x12 as a 16-bit LE pointer to a (sat_name, sat_color) table in ROM.

This sprint confirms that system end-to-end:
1. Find all entity types with +0x0C bit2 set during gameplay.
2. For each, read the ROM animation table at +0x11:+0x12.
3. Map table entries to sprite pattern names.
4. Update `kb/guides/entity-sprite-mapping.md` with the animation sequences.

## Inputs

- `kb/data/entity_table.md` (sprint 0021) — bit2 dispatch, field layout
- `kb/guides/entity-sprite-mapping.md` — type→pattern table; type 35 known to
  have +0x11:+0x12 = 0x84D1, +0x10 = 6 frames
- `kb/guides/zanac-sprite-names.md` — pattern index → sprite name

## Verification plan

```python
# tools/sprint0024_anim.py
# 1. Boot, wait for title (ROM mapped).
# 2. Read type-35 animation table directly from ROM.
# 3. Play briefly, dump all slots with +0x0C bit2 set and unique table addresses.
```

## Expected output

- Animation table at 0x84D1 decoded (type 35, 6 frames).
- List of other bit2 entity types with their table addresses.
- Updated `entity-sprite-mapping.md` with "Patterns that cycle / animate" expanded.

## Summary

### Method
Two-phase: (1) direct ROM read of the type-35 table using `msx.read_memory(0x84D1, 12)` after boot; (2) gameplay capture scanning all entity slots for `+0x0C & 0x04` with non-zero table pointer, then reading each table from ROM.

### Findings

**Two entity types confirmed using entity_update bit2 animation:**

| Type | Role | Table | Frames | Tick rate |
|------|------|-------|--------|-----------|
| 35 | Enemy projectile | 0x84D1 | 6 | 4 frames/step |
| 60 | Player death explosion | 0x86F3 | 11 | 4 frames/step |

**Type 35 — pulse animation:** lead→med_circle→lg_circle→med_circle→lead cycling through colors 0x8A→0x8E→0x8F→0x8D→0x89. Frame 0 (0xD0, 0x48) overlaps with a `JP 0x48D0` instruction byte pair; init sets +0x0F=1 to skip it. After frame 5 wraps to 0, one brief stealth_compl flash occurs before resuming.

**Type 60 — player death explosion:** 11-frame expanding-then-contracting sequence (invisible→lead×2→med_circle×2→lg_circle×2→med_circle×2→lead×2). +0x0C=0x04 (bit2 only, no motion). Explosion stays at player's last position. Previously "unknown / guess" in the jump table — upgraded to confirmed.

**Frame 0 / code-overlap pattern:** Both tables have frame 0 overlapping with Z80 instruction bytes in ROM (a `JP` instruction operand and a `RET` opcode respectively). This is deliberate — the init code sets +0x0F ≥ 1 to skip those bytes as display frames.

### What was updated
- `kb/guides/entity-sprite-mapping.md`: "Patterns that cycle / animate" section fully rewritten with decoded tables.
- `kb/data/entity_jump_table.md`: type 60 upgraded from guess → confirmed (player death explosion).

### Remaining unknown bit2 entities
Only 2 types found in a brief capture. Other animated entities almost certainly exist (loga, luster, veybar, spinner all have multi-frame sprite names). A longer capture or injection sprint should reveal more.
