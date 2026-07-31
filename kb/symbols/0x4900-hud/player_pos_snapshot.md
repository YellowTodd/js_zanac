---
address: 0x4C8B
end: 0x4CF6
kind: routine
name: player_pos_snapshot
confidence: confirmed
calls:   [0x4C91, 0x4CF7]
called_by: []
tags: [player, collision, entity]
sprint: "0044"
---

# player_pos_snapshot

> **Role correction (2026-07-30): 0x4C8B is "aim at the player and set the
> velocity", not a snapshot.** The `JP 0x4CF7` this entry called a "tail-call to
> continuation" is [[set_velocity_from_dir]] — the entry's own `calls:` list
> already said so. The body at 0x4C91 computes a full **16-way direction index
> toward the player** and 0x4C8B then writes the velocity from it, scaled by the
> entity's speed byte (+0x17).
>
> This resolves the type-44 velocity question: `handler_type44` (0x82D0) sets
> `+0x17 = (R & 3) + 1` and then calls 0x4C8B, so a fresh ground attacker
> launches **toward the player at speed 1–4**. Any handler whose init "just
> snapshots the player" in older notes actually aims at them.
>
> Direction computation (0x4C91–0x4CF6), past the point the analysis below
> stopped:
>
> ```
> 4CB8  C = |dy|  (0 -> 1)             ; bit2 of E128 set if player above
> 4CB9  A = playerX - entityX          ; bit3 set if player left, |dx| (0 -> 1)
> 4CCC  CP C: if |dx| >= |dy| swap, SET bit4   ; ratio <= 1, axis-swap flag
> 4CD7  HL = min<<8; E = max; CALL div_hl_e    ; ratio = min*256/max (8-bit)
> 4CDF  B=3; walk dir_angle_thresholds (0x4D42 = 50,106,171); octant = B left
> 4CEB  E = dir_remap_table[octant | E128 flags]   ; 0x4D45, 32 entries
> 4CF5  RET -> 0x4C8B does JP set_velocity_from_dir
> ```
>
> The octant + three flag bits (above/left/swap) index the 32-entry remap to a
> 0–15 direction; spot checks line up (e.g. flags 0/octant 3 → dir 4 = straight
> down toward a player below; swap-flag entries give the shallow angles).
> `0xE128`'s bits are therefore **aim quadrant flags**, not collision flags —
> though bit 2 ("player above") is also what the older note observed.
>
> A rename to `aim_at_player` is left for a `rename_symbol` pass; the name
> `player_pos_snapshot` fits only the two LD pairs at 0x4C91–0x4C9A.

## Summary

Reads the player entity's current Y and X positions from the entity slot
(0xE301 = Y, 0xE302 = X) and writes them to the game-state block at
0xE129/0xE12A. Then computes the direction from the current entity (IX) to the
player and sets the entity's velocity accordingly (see the correction above).

**Note:** function body lives in a DB block in the disassembler output
(source line 1183). Valid Z80 code starting at 0x4C8B.

## Analysis

```
4C8B  CALL 0x4C91     ; snapshot player Y/X → 0xE129/0xE12A
4C8E  JP 0x4CF7       ; tail-call to continuation

4C91  LD A, (0xE301)  ; player entity slot Y position
4C94  LD (0xE129), A
4C97  LD A, (0xE302)  ; player entity slot X position
4C9A  LD (0xE12A), A
4C9D  LD IY, 0xE128
4CA1  LD (IY+0x00), 0  ; clear collision flags
4CA5  LD A, (0xE129)   ; player Y
4CA8  SUB (IX+0x01)    ; − entity Y
4CAB  JP NC, 0x4CB4    ; if player >= entity: unsigned distance
4CAE  NEG              ; else: flip sign
4CB0  SET 2, (IY+0x00) ; flag: player is above entity
4CB4  JP NZ, 0x4CB8    ; if Y distance non-zero
4CB7  INC A            ; (rounding)
```

## Key variables

| Address | Role |
|---|---|
| 0xE129 | Player Y snapshot (from entity slot 0xE301) |
| 0xE12A | Player X snapshot (from entity slot 0xE302) |
| 0xE128 | Collision flag byte: bit 2 = player is above entity |

## Live confirmation (sprint 0044)

Reached during gameplay when homing entities are active (spawned type-10
dusters). Captured at 0x4C9D (after both copies): `0xE129 == 0xE301` and
`0xE12A == 0xE302` on every hit (e.g. player Y=160→E129=160, X=120→E12A=120),
confirming the player Y/X snapshot. `tools/sprint0044_verify.py`.
