---
address: 0x4C4D
kind: routine
name: update_status_bar
confidence: confirmed
calls:   [0x4C68, 0x4B83, BIOS:SETWRT, 0x4B8D]
called_by: [0x4C4A, 0x760C, 0x78FE, 0x8768]
sprint: "0047"
tags: [hud, video]
---

# update_status_bar

## Summary
Redraw the right-panel status readouts: **round**, **level** (shot upgrade), and
**lives**. Called whenever one of those changes (enemy/player handlers at
0x760C/0x78FE/0x8768, and the HUD-setup fall-through at 0x4C4A).

## Analysis
Source 0x4C4D:
```
4C4D  CALL render_round_digit   ; 0x4C68: round (E701) → 0x3A1B (2-digit)
4C50  LD A,(0xE10B)             ; shot_level
4C53  LD HL,0x39BB; CALL 0x4B83 ; level → 0x39BB (2-digit)
4C59  LD HL,0x397A; CALL SETWRT
4C5F  LD A,(0xE10A); OR A; RET Z ; lives 0 → done
4C64  DEC A; JP 0x4B8D          ; lives-1 → 0x397A (3-digit entry)
```

## Live confirmation (sprint 0047)
Micro-exec with E701=7, E10B=3, E10A=2: VRAM 0x3A1B=" 7" (round), 0x39BB=" 3"
(level), 0x397A shows the lives digit. `tools/sprint0047_verify.py`.
