---
id: "0025"
status: done
range: 0x7826-0x7E9C
strategy: live_debug
budget_turns: 25
---

# Sprint 0025 — Airborne enemy cluster (types 4–25)

## Goal

54 of the 89 entity types remain hypothesis or guess. The largest cohesive
group is the airborne enemy cluster: types 4–25 (plus 36–38 and a few others),
all in the 0x7826–0x7E9C handler range. With `entity_update` fully decoded
(sprint 0021) and the slot field semantics known, a live dump of entity slots
now yields enough information to classify any enemy.

This sprint targets the most-populated sub-groups:
- **Types 4–6** (0x7826): slow-spawn enemies — box-like? Same handler, 3 variants.
- **Types 7–9** (0x791D/0x79BE/0x79FB): umber-like, child pointer.
- **Types 16–17** (0x7BEB/0x7C8A): luster-like, R-bit direction.
- **Types 18** (0x7CB3): child-pointer countdown (+0x1D).
- **Types 22–25** (0x7D0F/0x7DB4): diagonal enemies (veybar?).

For each group: capture live slot data in gameplay, identify sprite pattern
from sat_name, classify motion from +0x0C and velocity fields, note child
pointer links.

## Inputs

- `kb/guides/entity-sprite-mapping.md` — patterns already confirmed for types
  4–10, 12–16, 19–25 (from sprint 0013/0015); but roles of types 18, 26–34
  still guess.
- `kb/data/entity_table.md` (sprint 0021) — full field semantics.
- `kb/data/entity_jump_table.md` — current hypothesis labels.
- Source around lines 3860–4100 (handler range 0x7826–0x7E9C).

## Verification plan

**Broad live capture:** let game run 90 seconds, capture entity table every
3 dispatch breaks, collect all slot data for types 4–37. For each type seen,
record:
- sat_name → pattern → sprite name
- +0x0C (behavior flags: homing/animate/motion)
- +0x08/+0x09 (vy), +0x0A/+0x0B (vx)
- +0x13/+0x15/+0x17 (homing fields, if bit3 set)
- +0x1B/+0x1C (child pointer)

```python
with ZanacGame.launch() as game:
    game.wait_for_title(); game.start_game()
    msx = game.client
    game.steer(up=True); time.sleep(1.0)

    seen: dict[int, list[bytes]] = {}
    bp = msx.set_breakpoint(0x445F,
        "incr ::n; if {$::n % 3 == 0} {debug break}")
    msx.cmd("set ::n 0")

    for _ in range(60):   # 60 breaks = 180 dispatch calls ≈ 3 min game time
        msx.cont(); time.sleep(0.4)
        raw = bytes(msx.read_memory(0xE300, 26*32))
        for i in range(26):
            slot = raw[i*32:(i+1)*32]
            typ = slot[0] & 0x7F
            if 4 <= typ <= 37 and typ not in (11, 35):
                seen.setdefault(typ, []).append(slot)
    msx.remove_breakpoint(bp)
```

**Per-type analysis:** for each observed type, print mean/variance of key
fields, group by +0x0C pattern and sprite name.

**Source spot-checks:** for types where live data is ambiguous, read 20 ROM
bytes from the handler entry and decode init sequence.

## Focus questions

- Are types 4–6 the box entities (pattern 53) in their running phase, or
  something else? (Sprite mapping already says type 5 = box confirmed.)
- What are types 26–34 (currently all "guess")? Do they appear in early game?
- Does type 18 use the child pointer for a complement sprite, and if so which?
- Can we confirm luster (29–32) for types 16/17?

## Expected output

- Updated `kb/data/entity_jump_table.md`: upgrade 10–20 entries from
  hypothesis/guess to likely/confirmed.
- Updated `kb/guides/entity-sprite-mapping.md` with new type→pattern rows.
- Possibly: new `kb/symbols/0x8000-enemy/handler_typeNN_*.md` for any fully
  decoded handler.

## Summary (filled at end)

Live capture (120 break-points × 30 frames ≈ 72 s game time, player invincibility held via RAM patch) collected slots for types 4–6, 10, 12–13, 21, 37. ROM static analysis covered types 7–9, 22–29.

**Confidence upgrades:**

| Types | Before | After | Method |
|-------|--------|-------|--------|
| 4, 5, 6 | hypothesis/likely | **confirmed** | Live: pattern 53, bflags=0x01, vy_frac=0xC0; ROM: complement 0xD8, +0x19=5 on activation |
| 10 | hypothesis | **confirmed** | Live: pattern 22, color 0x89, bflags=0x13; ROM: target_x from R-bit, complement 0x5C |
| 12, 13 | hypothesis | **confirmed** | Live: vy=−2, vx=+1/−2 direction split confirmed |
| 22–25 | hypothesis | **likely** | ROM: veybar init decoded — 22/23 Y-homing (0x09), 24/25 Y+X-homing (0x1B); R-bit spawn side; complement 0x98 |
| 26–29 | **guess** | **hypothesis** | ROM: large 4-frame animated sprite (pats 43–46), bflags=0x0F, spawn from screen edges, shared running code 0x7E3F |
| 37 | guess | **confirmed** | Live: pattern 7, color 0x8F, vy=−2 upward bullet |
| 38 | guess | **hypothesis** | ROM: spawned as burst of 7 by type-7 umber when stopped |
| 41 | guess | **hypothesis** | ROM: spawned as pair by type-8 when stopped |

**New structural findings:**
- `sub_4496` (0x4496) = `find_free_slot` — scans slots 5–25, returns HL or SCF
- `LAB_ram_8DDB` = `spawn_entity` helper — writes type A into found slot
- Type 9 periodically spawns type-20 (via +0x1D=8 countdown, calls 0x8DDB with A=0x14)
- Types 7/8 share running code at 0x7954; differentiated by type byte test after init
- Types 26–29 form two edge-swooper pairs with separate animation tables (0x7E68 color 0x8E, 0x7E70 color 0x87)

**Did not appear in capture:** types 7–9, 14–20, 22–29 (need longer game / later level). Type 9 (umber spawner) decoded via ROM.

**Files updated:** `kb/data/entity_jump_table.md`, `kb/guides/entity-sprite-mapping.md`
