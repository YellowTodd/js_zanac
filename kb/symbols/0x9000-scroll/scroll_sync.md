---
address: 0x9AE4
kind: routine
name: scroll_sync
confidence: likely
calls:   [0x42F8, 0x42ED]
called_by: []
tags: [scroll, vblank, timing]
sprint: "0008"
---

# scroll_sync

## Summary
Main-loop routine that enables VDP interrupts and spins until the ISR has
consumed the pending scroll DMA (bit 0 of 0xE700 cleared), then initialises
scroll state for the next frame. Effectively provides VBLANK synchronisation.

## Analysis
Source lines 4286–4298.

```
loop:
    CALL vdp_int_enable (0x42F8)   ; enable VDP interrupt
    LD A, (0xE700)
    BIT 0, A
    JR NZ, loop                    ; spin while DMA-ready bit is set
; ISR has cleared bit 0 → proceed
RES 3, A
LD (0xE700), A
LD BC, (0x0006)        ; VDP command port
CALL vdp_int_disable   ; disable VDP interrupt for state setup
SUB A
LD (0xE714), A         ; scroll_row ← 0 (start of new frame)
LD DE, 0xE800
LD (0xE715), DE        ; tile-row buffer ptr ← 0xE800
...
```

Called from multiple main-loop entry points (source lines 177, 322, 3179, 3405)
after scroll pre-computation. The loop-exit condition is set by `scroll_vram_write`
(0x9A79) which clears bit 0 when it finishes writing to the VDP name table.
