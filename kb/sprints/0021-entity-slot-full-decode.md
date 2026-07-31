---
id: "0021"
status: done
range: 0xE300-0xE63F
strategy: live_debug
budget_turns: 25
---

# Sprint 0021 — Entity slot full field decode (offsets 0x0C–0x1A)

## Goal

Complete the 32-byte entity slot layout for the four most important types:
- **Type 1** (player ship): motion, input flags, weapon state, invincibility timer
- **Type 2** (player shot): velocity, lifetime, pattern tracking
- **Type 44** (ground structure): tile position, scroll sync, shadow link
- **Type 39** (column marker): occupancy counter, parent link

Focus on the still-unknown offsets +0x0C through +0x1A for each type.
The sprint is **fully automatable headlessly**.

## Inputs

- `kb/data/entity_table.md` — slot layout confirmed to offset +0x0C (motion);
  +0x1B/+0x1C (child pointer); +0x1D (col-width counter). Gap: +0x0D–+0x1A.
- `kb/features/entity-sprite-mapping.md` — confirmed types and their patterns
- Sprint 0013 live dump: established slot stride=32, base=0xE300

## Verification plan

**Automated capture — 200-frame dump at entity_dispatch:**

```python
with ZanacGame.launch() as game:
    game.wait_for_title(); game.start_game()
    game.steer(up=True); game.shoot_both()

    frames = []
    msx.cmd("set ::dispatch_count 0")
    bp = msx.set_breakpoint(0x445F,
        "incr ::dispatch_count; "
        "if {$::dispatch_count % 10 == 0} {debug break}"
    )
    for _ in range(20):   # 20 breaks = 200 frames of data
        msx.cont()
        time.sleep(0.3)
        raw = msx.read_memory(0xE300, 26*32)
        frames.append(raw)
    msx.remove_breakpoint(bp)
```

Then for each type found in any frame, collect all 32 bytes and correlate:
- Offsets that change every frame → counters or velocity accumulators
- Offsets that change only on hit → HP / state machines
- Offsets correlated with Y/X position → fractional position bytes
- Offsets that are stable per entity → type-specific constants

**Cross-reference with source:**
For any confirmed type, use the handler address from `entity_jump_table.md` and
disassemble the handler to label writes to IX+n.

## Focus questions

- What is +0x0C for type 1 (player)? (Hypothesis: behavior flags from `entity_update`)
- What is +0x07/+0x0A/+0x0B? (Velocity fraction bytes based on motion formula)
- What is +0x13–+0x1A for type 44? (Column occupancy, tile offset, etc.)
- Does type 2 (shot) use a lifetime countdown, or is it cleared when it goes off-screen?

## Expected output

Updated `kb/data/entity_table.md` with confidence raised to `likely` or
`confirmed` for the +0x0C–+0x1A range.

## Summary

### Approach
Two live captures (`tools/sprint0021_capture.py` — 200-frame entity table dump at entity_dispatch; `tools/sprint0021_combat.py` — single snapshot with enemy activity) plus ROM machine code decoding of the entity_update routine (which Ghidra had rendered as raw DB bytes).

### entity_update (0x4898) fully decoded

The routine was embedded in a DB block after the credits text (not disassembled by Ghidra). Decoded by hand from lines 849–865 of the source. Five conditional calls on IX+0x0C bits, then always a SAT push:

| Bit | Address | Function |
|-----|---------|---------|
| 3 | 0x4942 | Y-homing: accelerate vy toward IX+0x13, +0x17 iterations/frame |
| 4 | 0x496B | X-homing: accelerate vx toward IX+0x14, +0x17 iterations/frame |
| 0 | 0x48DE | Y-motion: (Y:y_frac) += (vy:vy_frac); despawn if Y ≥ 208 |
| 1 | 0x48F8 | X-motion: (X:x_frac) += (vx:vx_frac); despawn if X ≥ 209 |
| 2 | 0x4912 | Animate: tick via +0x0D/+0x0E, frame index in +0x0F, table at +0x11:+0x12, loop at +0x10 |

**Corrected:** original entry in entity_table.md had bit0=update-X and bit1=update-Y reversed.

### entity_clear (0x48D0) boundary confirmed

entity_clear zeroes only **+0x00–+0x17** (24 bytes). Bytes **+0x18–+0x1F persist** across despawn. This explains why +0x18 can show the previous occupant's collision type until entity_post runs for the new occupant.

### Field decode: +0x0D–+0x17

| Offset | Name | Role |
|--------|------|------|
| +0x0D | anim_tick | Per-frame countdown (reloads from +0x0E when reaches 0) |
| +0x0E | anim_rate | Animation speed: frames per sprite change |
| +0x0F | anim_frame | Current animation frame index |
| +0x10 | anim_max | Total animation frames (loop wraps here) |
| +0x11:+0x12 | anim_ptr | 16-bit LE pointer to ROM animation table (sat_name, sat_color pairs) |
| +0x13 | target_y | Y-homing target position |
| +0x14 | target_x | X-homing target position |
| +0x15 | y_accel | Y-homing acceleration step |
| +0x16 | x_accel | X-homing acceleration step |
| +0x17 | homing_iters | Iterations of homing acceleration per frame; also handler-specific |

### +0x18 dual purpose

The collision routine at 0x4560 caches the entity's own type (bits 0–6) into +0x18 each time entity_post runs. Since +0x18 is in the persistent range, it may show a stale value from the previous occupant until entity_post fires.

Type-39 entities never call entity_post, so +0x18 is NOT the type cache for them. Instead, it is the **despawn countdown** set to 1 by the parent (type-44) via spawn_col_marker. The type-39 handler decrements it and calls entity_clear when it hits 0.

### Type-1 (player) invincibility confirmed from source

From source lines ~3544 (type-1 init code, found at 0x75D5):
- `LD (IX+0x17), 0x05` — constant 5 at spawn
- `LD (IX+0x1B), 0x40` — invincibility timer = 64 frames
- `SET 7, (IX+0x05)` — invincibility flag

From source lines ~3687 (running code):
- Each frame: XOR sat_color 0x0E (flash), DEC +0x1B
- When +0x1B = 0: RES 7,(IX+0x05), restore color 0x8F

### Type-2 (player shot) despawn mechanism confirmed

entity_update's Y-motion routine at 0x48DE checks `LD A, H; CP 0xD0; RET C; JP 0x48D0`. When Y < 208, continue. When Y wraps past 0 (negative velocity, Y becomes ≥ 208 as unsigned), entity_clear is called. **No countdown timer involved.**

### Type-44 (ground structure) init confirmed

From source lines ~4985–5001 (0x82D0 handler):
```
CALL 0x71DA        ; spawn_col_marker
LD (HL), 0x44      ; set col-marker sat_name
CALL 0x71C5        ; random_x_pos
LD A, R / AND 0x03 / INC A
LD (IX+0x17), A    ; +0x17 = random 1–4
LD (IX+0x0C), 0x03 ; bit0 + bit1 (Y-motion + X-motion)
LD (IX+0x03), 0x40
LD (IX+0x04), 0x83
SET 7, (IX+0x00)
```
Running code: entity_update → 0x71F6 → entity_post. Very simple.

### Remaining uncertainties
- +0x0D–+0x12 for type-1 (player): these fields grow over time (observed in live capture) but entity_update's animation is not triggered (+0x0C=0). The setting mechanism was not found in the visible player handler code; likely in a subroutine called from it or via an interrupt path.
- +0x17 for type-1 (player) = 5: not used by entity_update (no homing bits set). Purpose for the player unclear.
- +0x19–+0x1A: never observed non-zero for types 1/2/39/44.
- +0x71F6 subroutine called from type-44 running code: purpose not decoded.

### What was added / updated
- `kb/data/entity_table.md`: full field table rewritten with +0x0D–+0x1F semantics, entity_update dispatch table, entity_clear boundary note, type-specific init summaries.
- Bit0/bit1 behavior_flags swap corrected.
- Persistence of +0x18–+0x1F documented.

### Suggested next sprint
**Sprint 0024 — entity_update animation in practice**: pick 2–3 enemy types that use bit2 (animate), confirm their animation table addresses via openMSX memory read (msx.read_memory(addr, frames*2)), cross-reference with gfx_sprite_patterns. Also decode 0x71F6 (type-44 tile-place subroutine) to close the type-44 picture.
