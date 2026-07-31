---
address: 0x92CA
end: 0x92CF
kind: routine
name: clear_credits_busy
confidence: confirmed
inputs: {}
outputs: {}
clobbers: [AF, HL]
calls: []
called_by: [0x924E, 0x92A9]
tags: [ending, credits, e102]
sprint: "0033"
---

# clear_credits_busy  (sub_92ca)

## Summary
Tail routine of the ending sub-events: clears `E102` bit 2 and returns. Both
`LAB_91fd` (via `JP 0x92CA`) and the letter-draw phase (`CALL 0x92CA`) end here.

## Analysis
Source lines 7036–7039.
```
LD HL, 0xE102
RES 2, (HL)
RET
```
Bit 2 of `E102` is a transient "ending sub-event in progress" guard set by the
dispatcher (e.g. 0x91A4 `SET 2,(HL)`); each sub-event clears it on completion.
See [[ending_setup]].
