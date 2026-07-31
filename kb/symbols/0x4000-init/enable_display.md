---
address: 0x42E2
kind: routine
name: enable_display
confidence: confirmed
calls:   [0x0047]
sprint: "0043"
tags: [video, vdp]
---

# enable_display

## Summary
Set VDP register 1 BL bit → unblank the display.

## Analysis
Source lines 374–378. Reads VDP R1 shadow from (0xF3E0), sets bit 6, writes back via WRTVDP (0x0047) with C=1. Falls through to LAB_4301.

## Live confirmation (sprint 0043)
Micro-exec: after `disable_display` left `(0xF3E0)=0xA2`, calling 0x42E2 set it
to `0xE2` (bit 6 set), confirming it sets the BL display-enable bit.
`tools/sprint0043_verify.py`.
