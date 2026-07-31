---
address: 0x4306
kind: routine
name: wait_one_frame
confidence: confirmed
clobbers: [AF]
calls:   [0x42F8]
called_by: []
tags: [timing, vblank]
sprint: "0043"
---

# wait_one_frame

## Summary
Block until the next VBLANK fires, then return. Single-frame sync primitive.

## Analysis
Source lines 395–402.

```
CALL 0x42F8      ; vdp_int_enable (enables VDP interrupt generation)
LD A, (0xE1F8)   ; read frame_counter
SUB 0x1          ; set carry if A was 0
JR C, loop       ; loop while counter == 0 (carry means underflow)
SUB A            ; zero frame_counter
LD (0xE1F8), A
JP 0x42F8        ; tail-call vdp_int_enable again, then RET
```

The loop spins until `vblank_isr` has incremented 0xE1F8 to at least 1, then
clears the counter. Effectively waits exactly one VBLANK period.

Compare: `wait_frames` (0x5BEC) calls a structurally identical inner loop B times
for multi-frame delays.

## Live confirmation (sprint 0043)
Micro-exec with a return-trap: calling 0x4306 from a running game **returned**
(did not hang) with `(0xE1F8)=0x00` afterwards, confirming it spins on the ISR
frame flag and zeroes it on exit. A write-watchpoint on 0xE1F8 counted ≥8 writes
per 0.2 s (ISR + the wait loops). `tools/sprint0043_verify.py`.
