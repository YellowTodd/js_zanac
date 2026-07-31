---
address: 0x4996
kind: routine
name: render_lives_score
confidence: confirmed
calls:   [0x49B5]
sprint: "0047"
tags: [hud, score]
---

# render_lives_score

## Summary
Render current score (0xE105 hi) at VRAM **0x3809** and top score (0xE108 hi) at
**0x3815** via `render_score_bcd` (two calls).

## Analysis
Source 0x4996. `HL=0xE105; DE=0x3809; CALL render_score_bcd`; then
`HL=0xE108; DE=0x3815; JR render_score_bcd`.

## Live confirmation (sprint 0047)
Micro-exec with score=123456, topscore=654321: VRAM 0x3809="123456",
0x3815="654321". `tools/sprint0047_verify.py`.
