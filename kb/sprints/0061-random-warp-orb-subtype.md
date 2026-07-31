---
id: "0061"
status: done
range: 0x880D-0x88C1,0x8983-0x8A15
strategy: forward_from_caller
budget_turns: 15
subsystems: [M, G, H]
---

# Sprint 0061 — Destruction sub-type map, fire boxes & the round-0 totem

> **Subsystem slice:** [[M-secrets-and-warps]] / [[G-enemy-and-spawn-system]] /
> [[H-items-and-pickups]]. Originally scoped as "random-destination warp-orb
> sub-type", but decoding the destruction dispatch showed that premise was wrong
> (see below), so the sprint pivoted to the correct mechanics.

## Premise correction

Sprints 0059/0060 described the `0x88A2` `LD A,R & 7` path as a **random warp
destination**, and type-82 structures as "digit idols that warp to round 0".
Both were **wrong**. Decoding the destruction dispatch at 0x880D + a screenshot
pass settled it.

## Findings (decoded + live-confirmed)

**Destruction dispatch (0x880D), branch on `(IX+0x18)`, overwrites slot type:**

| `+0x18` | → | Spawns | Role |
|---------|---|--------|------|
| **< 0x51** (or 0x53) | 0x8833 | **type 72 ORB** (+ type-81 child) | eraser / **warp orb** |
| 0x51 | 0x8824 | type 0x50 (tbl 0x88C2) | structure part |
| **0x52** | 0x8874 | **type 0x53 fire** (SFX 0x12) | **fire dispenser** |
| 0x54–0x56 | 0x8854 | type 0x50 (tbl 0x88AB) | structure part |
| 0x57 / 0x58 | 0x8892 | type 0x50 (tbl 0x88B1 / 0x88CB) | structure part |
| ≥ 0x59 | 0x88A2 | **type 0x53 fire**, `+0x1C = R&7` | **random fire type** |

- **The `0x88A2` path is a random FIRE type, not a warp** — it jumps into the
  fire branch (0x8874 → type 0x53), feeding the random low byte into `+0x1C`
  (the fire number). There is no random-warp mechanism. Only `+0x18 < 0x51`
  spawns the orb.
- **Type 82 = fire-powerup box**, not a totem. Its `0xD2` foreground draw paints
  `0x30 + (IX+0x1C)` = the **fire-weapon digit**; on destruction (`+0x18=0x52`)
  it spawns a **type-83 black-shadow fire upgrade** ([[H-items-and-pickups]]).
  Screenshot: the two boxes at **round-1 start show "2" and "1"** (fire 2 & 1),
  broke on the digit draw (0x87F6) with `+0x1C=1`.
- **Totems:** type **71** = smiling totem (specific-round warp), type **70** =
  plain totem. Both become orbs (`+0x18 < 0x51`).
- **Round 0 in-game route** = the round-2 **type-70 "invisible totem"** (census
  idx 88, `+0x1C/1D = 0xA356` < 0xA751 → round 0, left of centre). Live-confirmed:
  `E722 = 0xA356` + `E102` bit 5 during round-2 play → `E701 → 0`, round 0 loaded
  (screenshot). This is the mechanic behind the player recipe now in
  [[idol-warp-orbs]].

## Verification

- Static: 0x880D dispatch + 0x8874/0x8892/0x88A2 branches decoded from ROM.
- Live: `tools/sprint0060_census.py` (type-70 round-0 totem @idx88/0xA356),
  a round-1 digit-box screenshot (`+0x1C=1` at 0x87F6), and a round-2 →
  `E722=0xA356` → `E701=0` warp screenshot.

## KB changes

- [[idol-warp-orbs]] — added destruction sub-type table, "Reaching round 0"
  (invisible totem), the player recipe, and a fire-dispenser section; corrected
  all type-82 / random-warp claims; guide `sprint: 0061`.
- [[handler_type70_wide_structure]], [[entity_jump_table]] (70/71/82),
  [[M-secrets-and-warps]] — type-82 = fire box, type-70 = plain/round-0 totem,
  random-fire correction.

## Summary

The "random warp sub-type" does not exist — 0x88A2 is a random fire type. Type 82
is the numbered fire-powerup box (digit = fire weapon), confirmed in code and by
screenshot. The only orb-spawning destruction branch is `+0x18 < 0x51`. Round 0
is reachable in-game via round-2's type-70 "invisible totem" (`0xA356` → R0),
live-confirmed, matching the player-reported R1→R2→R0 warp recipe.
