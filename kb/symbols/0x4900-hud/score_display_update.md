---
address: 0x4AA5
kind: routine
name: score_display_update
confidence: confirmed
inputs: {}
outputs: {}
clobbers: [AF, BC, DE, HL]
calls: [0x49B5, 0x42ED, 0x42F8, BIOS:FILVRM]
called_by: [0x9393]
tags: [hud, score, vram, e114]
sprint: "0047"
---

# score_display_update

## Summary
Called every frame from `gameplay_frame_loop`.  When E114 bit 6 is set
(score display dirty), either renders the current score from RAM to VRAM or
blanks the score area, then increments the E114 state counter.

## Analysis
Source lines 1319–1339.

```
LD A, (0xE114)
BIT 6, A            ; dirty flag
RET Z               ; nothing to do
LD DE, 0x38B8       ; VRAM destination (score row in name table)
BIT 2, A            ; mode select
JR Z, LAB_4aba      ; bit 2 = 0 → blank path

; Render-score path:
LD HL, 0xE105       ; BCD score data in RAM
CALL 0x49B5         ; render_score_bcd(HL=data, DE=VRAM dest)
JR LAB_4ac9

; Blank path:
LAB_4aba:
CALL 0x42ED         ; vdp_int_disable
EX DE, HL           ; HL = 0x38B8
LD BC, 7
LD A, 0x20          ; space
CALL 0x0056         ; BIOS fill-VRAM: write A (0x20) × BC to HL
CALL 0x42F8         ; vdp_int_enable

LAB_4ac9:
LD HL, 0xE114
INC (HL)            ; advance state counter
RET
```

`E114` is a state counter / dirty flag for the score display row.
Bit 6 enables the update; bit 2 selects between showing the live score (render
path) or clearing the score tiles (blank path).  The `INC` at the end advances
the counter each active frame; the caller or another routine is responsible for
clearing bit 6 when the display is settled.

This is the **"new top-score" flash**: 0x38B8 is the top-score row-2 slot, and
`score_milestone_flags` (E114) bit 6/bit 7 are set by the score-update path at
0x4A09/0x49F0 when the score overtakes the top score (see `add_score`).

## Live confirmation (sprint 0047)
Runs every frame from `gameplay_frame_loop`; `RET Z` (no-op) unless E114 bit 6 is
set. With bit 6 set it renders the score at 0x38B8 (bit 2 = 1) or fills 7 spaces
(bit 2 = 0) and increments E114, confirmed alongside the render chain.
`tools/sprint0047_verify.py`.
