---
address: 0x41CB
end: 0x41DA
kind: routine
name: clear_title_state
confidence: confirmed
inputs: {}
outputs: {}
clobbers: [AF, BC, HL]
calls:   []
called_by: [0x41BA, 0x41DB, 0x4110]
tags: [init, title-screen]
sprint: "0019"
---

# clear_title_state

## Summary
Zeroes 48 bytes at 0xE180–0xE1AF (the title-animation display buffer), then
sets bit 0 of 0xE700 (DMA trigger flag).

## Analysis
Source lines 251–260.

```
LD  HL, 0xE180
LD  B,  0x30       ; 48 bytes
loop:
    LD (HL), 0x00
    INC HL
    DJNZ loop
LD  HL, 0xE700
SET 0, (HL)        ; set E700 bit 0 = DMA trigger
RET
```

The 0xE180–0xE1AF region holds per-frame display state used by the title
animation (not the sprite-attribute shadow, which lives at 0xE000). Zeroing it
resets all pending tile/scroll updates.

0xE700 bit 0 is the "DMA active" flag polled by the VBlank ISR to decide
whether to run the SAT DMA to VRAM this frame.

Called from `title_screen_init` (0x41DB) during setup and from `sub_41BA`
(the per-frame countdown for the demo-mode attract sequence) once its
counter expires.

## Corrections (2026-07-30)

- **Caller.** 0x40E8 is `LD A,0x0B`; the real call site inside
  [[level_complete_handler]] is **0x4110**.
- **0xE180-0xE1AF is not title-animation state.** It is the per-row VRAM-blit
  control table for `scroll_vram_write` (the VBlank path loads `IY = 0xE180`
  at 0x9A82): `0xE180 + row` is the partial-write tile count (0 = write the
  full 24-tile row) and `0xE198 + row` the skip/resume offset read as
  `(IY+0x18)` at 0x9AD1. 0x30 bytes = two 24-row tables. This is the mechanism
  that shields the "ROUND n" banner from the scrolling blit.
- **0xE700 bit 0 is "a tile row is ready", not a SAT-DMA flag.** Its consumer
  is `scroll_vram_write` (0x9A79), which blits the 0xE800 ring into the **name
  table**. [[scroll_state]] has this right; this file disagreed with it.
