---
address: 0x97E3
end: 0x980D
kind: routine
name: scroll_precompute
confidence: confirmed
inputs:  {}
outputs: {}
clobbers: [AF, BC, HL, IX]
calls:   [0x9888]
called_by: []
tags: [scroll, vblank, timing]
sprint: "0010"
---

# scroll_precompute

## Summary

Per-frame routine that decrements `scroll_row`, resets the tile-buffer pointer,
calls the tile-row computation helper at 0x9888, then sets bits 0 and 1 of
`scroll_flags` (0xE700) to signal to the ISR that the tile buffer is ready.

## Analysis

Source lines ~4220–4232 (approximate; scroll_map_reader area).

```
97E3  LD C, (IX+0x14)       ; C = scroll_row (0xE714)
97E6  LD HL, (0xE715)       ; HL = tile_buf_ptr
97E9  DEC C                 ; scroll_row--
97EA  JP M, 0x97F3          ; if underflow (was 0 → C=0xFF < 0) → reset
97ED  LD DE, 0xFFE8         ; DE = -24
97F0  ADD HL, DE            ; tile_buf_ptr -= 24
97F1  JR 0x97F8
; ── reset path (triggered when scroll_row underflows past 0) ──
97F3  LD C, 0x17            ; C = 23 (new scroll_row)
97F5  LD HL, 0xEA28         ; HL = tile-LUT base address (reset)
; ── common path ──
97F8  RES 0,(IX+0)          ; clear bit 0 of scroll_flags (belt+suspenders)
97FC  LD (IX+0x14), C       ; scroll_row ← C
97FF  LD (0xE715), HL       ; tile_buf_ptr ← HL
9802  CALL 0x9888           ; compute tile row into buffer
9805  SET 0,(IX+0)          ; SET bit 0 = DMA-ready signal ← confirmed Q1
9809  SET 1,(IX+0)          ; SET bit 1 = secondary signal
980D  RET
```

## Verification

Live debug (sprint 0010) confirmed via passive write-watchpoint on 0xE700.
The per-frame 0xE700 write sequence:

| PC (CB byte) | Instruction | Before→After | Role |
|---|---|---|---|
| 0x948B | RES 1 | 0x02→0x00 | Frame start clear |
| 0x97F9 | RES 0 | 0x00→0x00 | Pre-clear (no-op if already 0) |
| **0x9806** | **SET 0** | **0x00→0x01** | **DMA-ready signal** |
| 0x980A | SET 1 | 0x01→0x03 | Secondary signal |
| 0x9A87 | RES 0 (in scroll_vram_write) | 0x03→0x02 | ISR clears bit 0 after writing VRAM |

Bit 1 is later cleared by `RES 1,(IX+0)` at 0x948A on the next frame.

## Notes

- IX = 0xE700 (`scroll_state` base) is established by callers, confirmed by disasm at 0x9486.
- `scroll_row` counts down from 23 to 0 then resets, giving a 24-row write cycle.
- The secondary SET 1 at 0x9809 purpose is not yet decoded; it is cleared by
  0x948A at the start of the next frame before any read of bit 1 is confirmed.
