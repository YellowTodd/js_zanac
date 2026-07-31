---
address: 0x752f
end: 0x7543
kind: data
name: fire2_special_table
confidence: confirmed
sprint: "0048"
tags: [fire, weapon, table]
---

# fire2_special_table

## Summary

7-entry table (3 bytes each) read only when `fire_num == 2`, inside
[[fire_select]] (0x7548, branch at 0x7579). Indexed by **E10B** (shot power
level) ×3, with **+3 added when the round (E701) ≥ 5**; the resulting 3-byte
record is passed to 0x97bc. Holds the per-power-level / late-round parameters for
fire weapon 2.

## Layout

```
0x752f: 38 1e 1e | 42 02 78 | 3a 28 3c | 1e 1e 1e | 41 0a c8 | 0a 64 14 | 43 0a 50
```

Immediately follows [[fire_init_table]] (0x751f).

## The three fields, resolved (2026-07-30)

`0x7591` passes the record to **`sub_97BC`** - the *same* single-record helper
[[level_script_format]] command 1 uses. So the record is
`[enemy type][count][fire interval]` and it becomes an entity of type **0x45
(69)**, the invisible wave emitter [[base_spawner_active]].

**Taking fire weapon 2 summons an enemy wave.** The row is the shot power
level, with **+3 entries once the round reaches 5** (0x7589), so the price
scales with how strong the player already is and how deep the run has got:

| level | round < 5 | round >= 5 |
|-------|-----------|------------|
| 0 | type 56 x30 every 30f | type 30 x30 every 30f |
| 1 | type 66 x2 every 120f | type 65 x10 every 200f |
| 2 | type 58 x40 every 60f | type 10 x100 every 20f |
| 3 | type 30 x30 every 30f | type 67 x10 every 80f |

Very much in the spirit of the [[alc-adaptive-difficulty]] system: the game
charges for a strong weapon in enemies rather than in ammo.
