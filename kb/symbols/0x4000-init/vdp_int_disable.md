---
address: 0x42ED
kind: routine
name: vdp_int_disable
confidence: confirmed
calls:   [0x0047]
called_by: [0x41DB, 0x43DA, 0x4343, 0x49B5, 0x4C4D, 0x4C68, 0x4DA5, 0x5C25]
sprint: "0019"
tags: [video, vdp]
---

# vdp_int_disable

## Summary
Clear VDP register 1 IE bit → disable VDP interrupt. Call before VRAM writes.

## Analysis
Source lines 380–385, called at lines 407, 683, 774, 933, 1105, 1160, 1338, 1384. Reads word from (0xF3DF); B = byte at 0xF3E0 (VDP R1 shadow). Clears bit 5 (IE). Writes B to VDP R1 via 0x0047 (WRTVDP), C=1. Pattern: CALL vdp_int_disable → CALL WRTVRM → later CALL vdp_int_enable.
