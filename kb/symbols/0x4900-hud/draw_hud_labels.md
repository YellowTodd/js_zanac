---
address: 0x4BD4
end: 0x4C4C
kind: routine
name: draw_hud_labels
confidence: confirmed
inputs: {}
outputs: {}
clobbers: [AF, BC, DE, HL]
calls:   [0x42ED, 0x4BC7, 0x49B5, 0x4996, 0x49AF]
called_by: [0x427B]
sprint: "0047"
tags: [hud, video, text, init]
---

# draw_hud_labels

## Summary
Draws the static right-panel HUD layout once at screen init (called from 0x427B):
the vertical border column plus the fixed text labels (**ALC, TOP, SCORE, ZANAC,
LEVEL, ROUND, FIRE**) and the initial score/top-score values. The dynamic
readouts are refreshed afterward by `update_status_bar` / `render_*` each time a
value changes.

## Analysis
Source 0x4BD4: `vdp_int_disable`; draw a 14-row (`B=0xE`) border column starting
at VRAM 0x3958, step `DE=0x20`, via `draw_hud_label_str` (0x4BC7); then a series
of `draw_hud_label_str` calls placing the individual labels at fixed name-table
addresses (0x38F9 "SCORE", 0x3899, 0x3999, …). Falls through the closing label
calls (0x4C2C–0x4C44) into `render_score_row2` (0x4C4A) and then
`update_status_bar` (0x4C4D).

`draw_hud_label_str` (0x4BC7) wraps the inline-string writer `0x5C28` (a
`vdp_set_addr_write` alt entry): the null-terminated tile string follows the
`CALL` in ROM (which is why this region disassembles as mixed code/data).

## Live confirmation (sprint 0047)
Micro-exec at 0x4BD4 wrote the label tiles to VRAM — e.g. 0x38F9 = "SCORE ".
The full label set is visible in the in-game / credits screenshots (sprint 0046:
ALC / TOP / SCORE / ZANAC / LEVEL / ROUND / FIRE). `tools/sprint0047_verify.py`.

## See also
- `vdp_set_addr_write.md` (0x5C28 alt entry) — the inline-string writer.
- `update_status_bar.md`, `render_lives_score.md` — dynamic value refresh.
