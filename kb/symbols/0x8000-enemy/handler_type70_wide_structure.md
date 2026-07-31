---
address: 0x87ab
end: 0x8947
kind: routine
name: handler_type70_wide_structure
confidence: confirmed
inputs:  { IX: "entity slot" }
outputs: {}
clobbers: [AF, BC, DE, HL, IY]
calls:   [0x8f25, 0x8948, 0x42ed, 0x0053, 0x5bfc, 0x42f8, 0x44ca, 0x7904, 0xbfc8, 0x4a6a, 0x4496, 0x8ddb]
called_by: [0x445f]
tags: [entity, enemy, base, ground-structure]
sprint: "0052"
---

# handler_type70_wide_structure

Shared handler for the **wide ground-structure / base wall** segments: types
70–71, 81–82, 87–89 — the shootable ground **idols** (see [[idol-warp-orbs]]).
These are the large multi-tile structures that make up a base. Each segment waits
for the scroll to bring it on-screen ([[wide_struct_init]] 0x8f25), draws its
tile directly into VRAM, takes hits via the box hit-sub (0x7904), and on
destruction branches by its +0x18 sub-type to spawn the next piece or hand off to
the base-encounter counters.

On activation (0x87B0) it reads **`(0xE720)[(IX+0x03)]` → `(IX+0x1C/1D)`** — the
per-round idol table (set by map-script cmd 8). For sub-types that spawn a
**type-72 orb** (0x880D branch), that `+0x1C/1D` becomes the orb's **warp
destination** (a stream pointer); a black orb touched by the player warps to the
round it resolves to. Per-round destinations catalogued in [[idol-warp-orbs]].

**Type-82 = fire-powerup box (0x87E2–0x8806):** only entity **type 82**
(`(IX+0x00)==0xD2`) paints an extra foreground tile `0x30 + (IX+0x1C)` at its
position (HP-band test at 0x87C7: <0xC8→HP 6, 0xD2→HP 4, else HP 3). `+0x1C` is a
**fire-weapon number**, so this renders a **digit glyph** on the box (round 1's
two boxes show "2" and "1"). On destruction its `+0x18 = 0x52` takes the 0x8874
branch → slot becomes **type 0x53 (black-shadow FIRE upgrade)** + SFX 0x12. So
type 82 is the blue **fire-powerup dispenser**, *not* a totem/idol.

**Destruction dispatch (0x880D)** — branches on `+0x18` and overwrites the slot
type: `< 0x51` → **type 72 orb** (the eraser/warp orb; +spawns a type-81 child);
`0x51/0x54–0x58` → type 0x50 explosion + crater; `0x52` → type 0x53 fire; `≥ 0x59`
(0x88A2) → type 0x53 fire with `+0x1C = R&7` (**random fire type**, *not* a random
warp). Full table + the round-0 "invisible totem" in [[idol-warp-orbs]].

**Crater stamps (0x88ED, byte-exact 2026-07-30):** every non-orb branch leaves
debris tiles behind, stamped into **both** the scroll ring and the name table so
the wreckage scrolls away with the terrain. Strip format: `[rowCount]` then per
row `[width][tiles…]` (tiles 0x3A–0x3E); entry coords come in `H = X − ofs`,
`L = Y − ofs` and 0x8948 converts to the cell. The strips **overlap in ROM** to
save bytes and end exactly at the stamper's first instruction:

| sub-type | strip | size | coords | slot becomes |
|----------|-------|------|--------|--------------|
| 0x51 | 0x88C2 | 2×3 | (X−0x24, Y−0x10) | 0x50 explosion |
| 0x52 | 0x88D8 | 4×4 | (X−0x28, Y−0x18) | 0x53 shadow + SFX 0x12 |
| 0x54–0x56 | word\[0x88AB + (n−0x54)·2\] → 0x88B1/0x88B8/0x88C2 | 2×2 / 3×2 / 2×3 | (X−0x20, Y−0x10) | 0x50 |
| 0x57 | 0x88B1 | 2×2 | (X−0x20, Y−0x10) | 0x50 |
| 0x58 | 0x88CB | 3×3 | (X−0x20, Y−0x10) | 0x50 |
| ≥0x59 | 0x88D8 | 4×4 | (X−0x28, Y−0x18) | 0x53 shadow, `+0x1C = R&7`, SFX 0x12 |

Only the shadow (0x8874) and orb (0x8833) paths call `add_score_for_subtype`
(0x4A6A) — the plain explosion paths score nothing at dispatch.

> **Corrections (0060/0061):** the specific-round **warp totems** (→ R1/R3/R4/R6/R8,
> incl. backward R2→R1 & R5→R4) are entity **type 71** (grey "smiling totem",
> census + screenshot). Type **70** = plain totem (round-0 dests). Type **82** =
> fire box (screenshot-confirmed). The 0059 "0xD2 = warp marker" and the 0x88A2
> "random *warp*" claims were both wrong. See [[idol-warp-orbs]].

```
87ab  CALL 0x8f25 / JR C,0x8806           ; gate: wait for scroll (else just post)
87b0  LD A,(IX+0x03) / … LD HL,(0xe720)+A  ; per-segment table in RAM (0xe720)
87bb  LD (IX+0x1c),A / (IX+0x1d) = next byte
87c3  LD (IX+0x03),0x24                     ; structure tile pattern (entry shared by 84–86)
87c7  set +0x19 (HP) from Y-position bands (0xc8/0xd7/0xd2 thresholds)
87e2  compute VRAM addr (0x8948) → write tile (SETWRT/0x5bfc inside int-disable)
8806  CALL 0x44ca                           ; post (SAT + collision)
8809  CALL 0x7904 / RET NZ                  ; hit-sub; survived → return
880d  LD A,(IX+0x18) / LD (IX+0x00),0x48     ; destroyed → branch by sub-type:
       0x51→spawn (table 0x88c2) / 0x54.. / 0x57.. → sub-parts;
       0x8833 path: CALL 0xbfc8 (encounter) + 0x4a6a + spawn children
```

## Related

[[wide_struct_init]] (0x8f25), [[handler_type84_wide_variant]] (joins at 0x87c3),
[[handler_type4_box]] (0x7904 hit-sub), [[entity_jump_table]] (70–71/81–82/87–89).
