---
address: 0x42D7
kind: routine
name: disable_display
confidence: confirmed
calls:   [0x0047]
sprint: "0043"
tags: [video, vdp]
---

# disable_display

## Summary
Clear VDP register 1 BL bit → blank the display.

## Analysis
Source lines 368–373. Reads VDP R1 shadow from (0xF3E0), clears bit 6 (BL=display enable), writes back to VDP via WRTVDP (0x0047) with C=1.

## Live confirmation (sprint 0043)
Micro-exec from in-game state: pre-call R1 shadow (0xF3E0) had bit 6 set;
after calling 0x42D7, `(0xF3E0) = 0xA2` (bit 6 clear), confirming it clears the
BL display-enable bit. `tools/sprint0043_verify.py`.
