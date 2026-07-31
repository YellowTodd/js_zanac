---
address: 0x93AB
end: 0x93E3
kind: data
name: base_attack_patterns
confidence: confirmed
sprint: "0065"
tags: [enemy, base, attack-pattern, data-table, g-enemy]
---

# base_attack_patterns (0x93AB–0x93E3, 57 B)

## Summary

The **base-attacker movement-pattern table**: 8 patterns assigned round-robin
to the attacker entities a base spawns. Two parts:

```
0x93AB–0x93BA  8 pointer words  -> point into the descriptor block below
0x93BB–0x93E3  8 variable-length descriptors (3-byte records, 0x00-terminated)
```

Every one of the 57 bytes is accounted for (16 pointer + 41 descriptor).

## Reader — `base_attack_spawn` (0x8FDE)

Reached from the global base-encounter controller (`SUB_ram_8f5e` 0x8F5E, run
with `IX=0xE100`) via 0x8FCA when the encounter counter `(IX+0x57)&0x1F` crosses
its threshold. It spawns up to `(IX+0x51)` attackers and hands each one a pattern
pointer, **round-robin**:

```
0x8FDE  HL = 0x93AB ; (0xE717) = HL        ; E717 = rotating pattern cursor
0x8FE4  C = 8                              ; 8 patterns before wrap
  per attacker (B = IX+0x51):
0x8FF1  HL = (0xE717)
0x8FF4  E = (HL); D = (HL+1)               ; read one pointer word
0x8FF8  if --C == 0: HL = 0x93AB; C = 8    ; wrap after 8
0x9000  (0xE717) = HL
0x9003  (IY+0x0F) = E ; (IY+0x10) = D      ; -> attacker's descriptor pointer
```

`0xE717` (`base_attack_cursor`) persists across calls, so successive base waves
draw successive patterns and cycle every 8. `IY` walks a 4-byte-per-entry list at
0xE780 selecting which entity slot each pattern is written to.

## Descriptor format — interpreted by `0x8BF5`

The attacker handler (0x8ADF: `L=(IX+0x0F); H=(IX+0x10); CALL 0x8BF5`) reads its
descriptor as a stream of **3-byte records**:

```
0x8BF5  A = (HL) ; if A==0 -> reload HL from (IX+0x0F/0x10) = LOOP to start
        (IX+0x09) = byte0    ; phase-0 rate
        (IX+0x0A) = byte1     ; mid-phase rate
        (IX+0x0B) = byte2     ; phase-3 rate
        (IX+0x11/0x12) = HL+3 ; saved "next record" cursor
```

The handler picks one of the three rate bytes per frame by the attacker's phase
`(IX+0x0C)` (0 → +0x09, 3 → +0x0B, else → +0x0A), accumulates it into `(IX+0x0E)`,
and on carry advances to the next record (0x8C15) — so each 3-byte record is a
`(rate0, rateM, rate3)` velocity triplet and a **`0x00` byte loops the pattern**.

### The 8 decoded patterns

| # | Ptr | Records `(r0,rM,r3)` … `00` |
|---|-----|------------------------------|
| 0 | 0x93BB | (04,30,02) 00 |
| 1 | 0x93BF | (04,20,03)(02,20,02) 00 |
| 2 | 0x93C6 | (04,1C,02)(04,30,04) 00 |
| 3 | 0x93CD | (04,28,05) 00 |
| 4 | 0x93D1 | (05,40,0E) 00 |
| 5 | 0x93D5 | (04,10,0A)(03,20,05) 00 |
| 6 | 0x93DC | (02,20,08) 00 |
| 7 | 0x93E0 | (03,20,08) 00 |

## Confidence

`confirmed`. The reader (0x8FDE), cursor (0xE717) and interpreter (0x8BF5) are
disassembled and quoted; the 3-byte-record + `0x00`-loop model accounts for all
57 bytes. **Live-confirmed (sprint 0065, `tools/verify_base_clear.py`):** playing
round 1 to its one-eye base (invincible ship via `ZanacGame.make_invincible`;
the base encounter is signalled by the scroll row counter 0xE702 stalling),
`base_attack_spawn` (0x8FDE) fired and **21 descriptor reads at 0x8BF5 all landed
in 0x93BB–0x93E3**, walking 9 distinct positions (0x93BB, 0x93BE, 0x93BF, 0x93C2,
0x93C6, 0x93C9, 0x93CC, 0x93CD, 0x93D0) — record cursors advancing through
patterns 0–3 and cycling on the `0x00` loop byte (e.g. 0x93BE = pattern 0's
terminator), exactly as decoded.

## See also

[[structure_award_index_table]] (data_4b2a), [[base_clear_award_index_table]]
(0x9302), `handler_type72_base_core`, `handler_type73_base_segment`.
