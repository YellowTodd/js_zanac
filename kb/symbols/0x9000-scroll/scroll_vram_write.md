---
address: 0x9A79
end: 0x9AA5
kind: routine
name: scroll_vram_write
confidence: likely
calls:   [0x0053, 0x9AA6]
called_by: [0x43DA]
tags: [scroll, vram, vblank, name-table]
sprint: "0008"
---

# scroll_vram_write

## Summary
VBLANK ISR callback that transfers prepared tile-row data from RAM into the
VDP name table. Activated when bit 0 of (0xE700) is set; clears that bit on
entry (one-shot handshake with the main loop). Implements the circular-buffer
write needed for vertical scrolling with wrap-around.

## Analysis
Source lines 4279–4285 (DB block immediately after `LAB_ram_9a68`).
Called from `vblank_isr` (0x43DA+) as `CALL 0x9A79`.

### Entry
```
LD IX, 0xE700
BIT 0, (IX+0)   ; test DMA-ready flag
RET Z           ; return immediately if no scroll update pending
LD IY, 0xE180   ; per-row status array (48 bytes)
RES 0, (IX+0)   ; clear DMA-ready flag (handshake)
LD BC, (0x0007) ; VDP data port in C
LD DE, (0xE715) ; main tile-row buffer pointer
LD HL, 0x3800   ; name table VRAM base
```

### Scroll-split calculation
```
A = CPL(0xE714) + 25   ; rows from scroll position to end of table
CALL scroll_vram_inner ; write top portion from (0xE715)

A = (0xE714)           ; rows at start of table (wrap-around)
RET Z                  ; no wrap needed
LD DE, 0xE800          ; secondary buffer for wrapped rows
fall-through to scroll_vram_inner with new DE
```

### scroll_vram_inner (0x9AA6): outer/inner DMA loops
Standalone entry: [[scroll_vram_inner]] (sprint 0033).
```
B = A                        ; outer iteration count (rows to write)
CALL WRTVRM (HL)             ; set VDP write address to current row start
for B iterations:
    if (IY+0) == 0:          ; simple (non-split) row
        OUT 24 bytes from DE ; copy tile data to VDP
    else:                     ; split row (wraps tile-column boundary)
        OUT (IY+0) bytes from DE      ; first segment
        ADD HL, (IY+0x18)*BC          ; advance VDP row position
        CALL WRTVRM                   ; reset VDP write address
        OUT (24 − (IY+0x18)) bytes    ; second segment
    HL += 32                  ; next name table row (32 bytes/row)
    INC IY                    ; next per-row status entry
```

### DMA handshake with main loop
Bit 0 of (0xE700) is SET by the main loop (scroll pre-computation) when a new
tile row is ready in the buffers. The ISR clears it after the VRAM write. The
main-loop sync routine `sub_9ae4` (0x9AE4) enables VDP interrupts and spins
until bit 0 is clear, achieving VBLANK synchronization.

## State variables used
| Address | Role |
|---------|------|
| 0xE700 bit 0 | DMA-ready flag (set by main loop, cleared here) |
| 0xE714 | Vertical scroll row counter (0–23); split position |
| 0xE715 | 16-bit ptr to main tile-row buffer (24 bytes per row) |
| 0xE800 | Secondary tile-row buffer (wrap-around rows) |
| 0xE180–0xE1AF | Per-row status array; 0=simple, non-zero=(IY+0x18)=split offset |
