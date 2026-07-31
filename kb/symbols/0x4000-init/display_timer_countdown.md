---
address: 0x41BA
end: 0x41CA
kind: routine
name: display_timer_countdown
confidence: confirmed
inputs: {}
outputs: {}
clobbers: [AF, HL, B, IX]
calls: [0x41CB]
called_by: [0x4099]
tags: [main-loop, timer, e102, title]
sprint: "0034"
---

# display_timer_countdown  (SUB_41BA)

## Summary
Per-frame countdown for the timed display state (`E102` bit 4). Decrements the
counter at `E15E`; when it reaches 0, clears the screen state and exits the
timed state by resetting bit 4.

## Analysis
Source lines 235–242.
```
LD IX,0xE100
DEC (IX+0x5E)          ; E15E -= 1
RET NZ                 ; still counting -> done for this frame
CALL 0x41CB            ; clear per-row status (0xE180), arm scroll DMA
LD HL,0xE102 ; RES 4,(HL)   ; clear display_timer flag -> leave timed state
RET
```

## Helper sub_41cb (0x41CB)
A small shared routine (also called by `level_complete_handler` and the game
init at 0x422F): zero the 48-byte per-row status array at `0xE180`
(`B = 0x30`), then `SET 0,(0xE700)` to request a scroll DMA write next VBLANK.
```
LD HL,0xE180 ; LD B,0x30 ; {LD (HL),0 ; INC HL} x48
LD HL,0xE700 ; SET 0,(HL) ; RET
```
The 0xE180 array is the simple/split per-row status consumed by
[[scroll_vram_inner]]; clearing it forces every row to the "simple 24-byte"
path for the next full repaint.
