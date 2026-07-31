---
address: 0x49AF
kind: routine
name: render_score_row2
confidence: confirmed
calls:   [0x49B5]
sprint: "0047"
tags: [hud, score]
---

# render_score_row2

## Summary
Render current score (0xE105 hi) at VRAM **0x3918** via `render_score_bcd`
(falls through into it).

## Analysis
Source 0x49AF: `LD HL,0xE105; LD DE,0x3918` → falls into `render_score_bcd`.

## Live confirmation (sprint 0047)
Micro-exec score=123456 → VRAM 0x3918="123456"; score=000042 → "    42".
`tools/sprint0047_verify.py`.
