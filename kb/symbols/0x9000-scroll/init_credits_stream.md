---
address: 0x9433
end: 0x9443
kind: routine
name: init_credits_stream
confidence: confirmed
inputs:
  HL: "ROM level-stream start pointer (e.g. 0xBBB4 for the credits screen)"
outputs:
  E701: "round/stage index of the matched level table entry"
clobbers: [AF, BC, DE, HL]
calls: [0x9444, 0x4C68, 0x941B]
called_by: [0x9216]
tags: [scroll, level-map, ending, credits]
sprint: "0045"
---

# init_credits_stream  (sub_9433)

## Summary
Points the level-stream engine at an arbitrary ROM level-data start (`HL`).
Used by `ending_setup` (`LAB_91fd`) with `HL = 0xBBB4` to load the credits
tile screen. Returns immediately if `HL == 0`.

## Analysis
Source lines 7192–7201.
```
LD A,H ; OR L ; RET Z            ; ignore null pointer
CALL 0x9444                      ; sub_9444: find stage index for HL in the
                                 ;   level table at 0x945C; returns A=index
LD (0xE701), A                   ; store stage index
PUSH HL ; CALL 0x4C68 ; POP HL   ; 0x4C68: VRAM/screen reset for the new level
JP 0x941B                        ; tail into sub_940c body: set E706/E702/E704
                                 ;   from the stream pointer, clear E700 bit 0
```
It sets up *streaming state* (E701/E702/E704/E706); it does **not** itself blit
VRAM pattern data. The actual tile columns are produced afterwards by
[[ending_setup]]'s call to `sub_946e` (24× `sub_94c3`).

## Live confirmation (sprint 0046)

Micro-exec with `HL = 0xBBB4` (the credits stream start `ending_setup` uses):
`E701` became **8** (= `resolve_round_from_ptr(0xBBB4)`) and the scroll-state
block changed (`E700..E707: 00011a005ba71e00 → 0008ffffb6bb0000`, i.e.
`E704:E705 = 0xBBB6 = HL+2`), confirming it arms the stream from the pointer.
With `HL = 0` it returned immediately leaving `E701` untouched (RET Z path).
`tools/sprint0046_verify.py`.

`resolve_round_from_ptr` (0x9444) scans `stage_stream_ptr_table` (0x945C) for the
round whose stream start matches `HL`, returning the round number — the same path
`LAB_40da` uses on a stage clear. See `resolve_round_from_ptr.md` and
`round-progression.md`.
