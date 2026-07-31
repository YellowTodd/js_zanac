---
address: 0x49A7
kind: routine
name: render_topscore_row2
confidence: confirmed
calls:   [0x49B5]
sprint: "0047"
tags: [hud, score]
---

# render_topscore_row2

## Summary
Render top score (0xE108 hi) at VRAM **0x38B8** via `render_score_bcd`.

## Analysis
Source 0x49A7: `LD DE,0x38B8; LD HL,0xE108; JR render_score_bcd`.

## Live confirmation (sprint 0047)
Micro-exec topscore=654321 → VRAM 0x38B8="654321". `tools/sprint0047_verify.py`.
