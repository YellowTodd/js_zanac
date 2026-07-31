---
address: 0x986E
end: 0x9887
kind: routine
name: copy_tile_column
confidence: likely
inputs:
  HL: "source 24x24 tile-grid base (row-major, stride 24)"
  C: "column index 0..23"
  B: "0 (BC = column offset into the grid)"
outputs: {}
clobbers: [AF, DE]
calls: []
called_by: [0x985A, 0x9862]
tags: [scroll, tile, logo, credits]
sprint: "0033"
---

# copy_tile_column

## Summary
Copies one **vertical column** of 24 tiles from a source 24×24 tile grid
(`HL`) into the live tile-row buffer at **0xE800**, at the same column index
`C`. Used by the end-credits logo-reveal animation to uncover the prebuilt
ZANAC-logo screen (held at 0xEB00) column-by-column.

## Analysis
Source lines 7586–7607.

```
PUSH HL ; PUSH BC
ADD HL, BC          ; HL = src + C
EX DE, HL           ; DE = src column pointer (row 0)
LD HL, 0xE800
ADD HL, BC          ; HL = 0xE800 + C  (dest column pointer, row 0)
LD B, 0x18          ; 24 rows
loop (LAB_9878):
    LD A, (DE) ; LD (HL), A      ; copy one tile
    LD BC, 0x18 ; ADD HL, BC     ; dest += 24  (next row, same column)
    EX DE, HL ; ADD HL, BC ; EX DE, HL   ; src  += 24
    DJNZ loop
POP BC ; POP HL ; RET
```

The grid is row-major with a 24-byte stride, so advancing by 24 each step walks
down one column. Source and destination use the **same** column offset `C`
(this is a straight column copy, not a transpose).

## Caller context (logo reveal, 0x9852–0x986D)
```
LD HL, 0xEB00            ; prebuilt credits/logo tile screen (built by LAB_91fd)
LD B, 0 ; LD C, (IX+0xD) ; column index from the reveal counter
CALL 0x986E             ; reveal column C
LD A, C ; CPL ; ADD A, 0x18 ; LD C, A   ; C' = 23 - C  (mirror column)
CALL 0x986E             ; reveal the mirror column
SET 0, (IX+0) ; SET 1, (IX+0)            ; flag the row buffer dirty for the ISR
```

So each frame of the reveal copies a symmetric pair of columns (`C` and
`23−C`) from the 0xEB00 logo screen into the visible 0xE800 buffer, wiping the
logo into view from the edges inward as `(IX+0xD)` advances.

## Cross-references
- 0xEB00 logo screen is assembled by the credits setup `LAB_91fd` (0x91FD) via
  [[scroll_map_reader]] / sub_946e and a VRAM stash/restore through 0x3C00.
- The dirty-flag handshake (bits 0/1 of 0xE700) is consumed by
  [[scroll_vram_write]] (see [[scroll_state]]).
