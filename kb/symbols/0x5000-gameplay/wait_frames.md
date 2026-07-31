---
address: 0x5BEC
kind: routine
name: wait_frames
confidence: confirmed
calls:   [0x42F8]
called_by: [0x8A26]
sprint: "0043"
tags: [timing]
---

# wait_frames

## Summary
Wait B VBLANK frames by polling the frame counter at 0xE1F8.

## Analysis
Source lines 1916–1925. Outer DJNZ decrements B. Inner loop: clears 0xE1F8, CALL vdp_int_enable (42F8), polls 0xE1F8 until non-zero. The VBLANK ISR increments 0xE1F8 once per frame. Thus each outer iteration waits exactly one VBLANK.

## Live confirmation (sprint 0043)
Micro-exec with B=20 from a running game blocked **0.30 s** of wall-clock before
returning (20 frames @59 Hz ≈ 0.34 s), confirming it waits B VBLANKs and is not
a busy spin. `tools/sprint0043_verify.py`.
