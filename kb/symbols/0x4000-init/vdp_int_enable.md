---
address: 0x42F8
kind: routine
name: vdp_int_enable
confidence: confirmed
calls:   [0x0047]
sprint: "0043"
tags: [video, vdp]
---

# vdp_int_enable

## Summary
Set VDP register 1 IE bit → re-enable VDP interrupt.

## Analysis
Source lines 386–394. Like vdp_int_disable but SETs bit 5. Both converge at LAB_4301 which calls WRTVDP (0x0047) and returns. Called via JP from several routines as a tail-call.

## Live confirmation (sprint 0043)
Micro-exec: after `vdp_int_disable` left `(0xF3E0)=0xC2` (bit 5 clear), calling
0x42F8 set it to `0xE2` (bit 5 set), confirming it sets the IE VDP-interrupt
bit. `tools/sprint0043_verify.py`.
