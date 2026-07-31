---
address: 0x4DA5
kind: routine
name: pause_handler
confidence: confirmed
inputs: {}
outputs: {}
clobbers: [AF, AF', HL]
calls: [0x0141, 0x5208, 0x42ED, BIOS:SETWRT, 0x005C, 0x4E0B, 0x42F8, 0x520E]
called_by: [0x9393]
tags: [pause, input, keyboard, stop-key, vram, e118, e102]
sprint: "0032"
---

# pause_handler

## Summary
Called every frame from `gameplay_frame_loop`.  Detects the STOP key (row 7
bit 4) and enters a blocking blink loop that halts entity dispatch and scroll
until STOP (or SELECT) is pressed again.

## Analysis
Source lines 1581–1658. Replaces incorrect sprint-0002 hypothesis (name was
`update_fire_display`; actual behaviour is pause, not fire-display animation).

```
LD A, 7
LD HL, 0xE118       ; pause-state byte
CALL 0x0141         ; SNSMAT(row=7) → A (0 = key pressed)
BIT 4, A            ; STOP key (row 7 bit 4)?
JR Z, LAB_4db4      ; Z set → STOP is pressed

; STOP not pressed:
RES 7, (HL)         ; clear re-entry guard
RET

LAB_4db4:
; STOP is pressed:
BIT 7, (HL)         ; re-entry guard (set = "already in pause transition")
RET NZ              ; guard set → ignore (prevents double-trigger)
BIT 6, A            ; SELECT key (row 7 bit 6)?
EX AF, AF'          ; stash SELECT flag
XOR A
LD (HL), A          ; zero E118 (reset pause state byte)
EX AF, AF'          ; restore SELECT flag
JR Z, LAB_4e37     ; SELECT held → skip PAUSE text, go directly to blink loop

; STOP only (no SELECT):
CALL 0x5208         ; mute sound
CALL 0x42ED         ; vdp_int_disable
LD HL, 0x396A       ; VRAM address of "PAUSE" tiles
LD DE, 0xE119       ; RAM source (cached "PAUSE" tile data)
LD BC, 5
CALL 0x0059         ; SETWRT + write 5 bytes → "PAUSE" appears

LAB_4dd1:           ; blink loop
LD A, (0xE118)
LD B, A
AND 0x0F            ; low 4 bits = sub-frame counter (0–15)
JR NZ, LAB_4df7     ; not a 16-frame boundary → skip toggle
BIT 4, B            ; "visible" phase bit?
JR NZ, LAB_4deb     ; → write "PAUSE" tiles
; Clear path: FILVRM with 0 → erase "PAUSE" text
LD DE, 0x396A
LD HL, 0x4E40       ; blank-tile source
LD BC, 5
CALL 0x005C         ; FILVRM 5 bytes
JR LAB_4df7
LAB_4deb:
; Set path: write "PAUSE" tiles back
LD DE, 0x396A
LD HL, 0xE119
LD BC, 5
CALL 0x005C         ; FILVRM 5 bytes

LAB_4df7:
CALL 0x4E0B         ; pause_frame_tick: advance E118 counter, re-read STOP key
JR NC, LAB_4dd1     ; carry clear → STOP not released yet, keep looping

; STOP pressed again (second press):
LD DE, 0x396A
LD HL, 0xE119
LD BC, 5
CALL 0x005C         ; restore "PAUSE" tiles (make them visible on exit)
JP 0x42F8           ; vdp_int_enable → return to caller
```

`E118` is the pause-state byte:
- Bits 0–4: 5-bit frame counter (incremented by `sub_4e0b`, wraps at 0x1F).
- Bit 4: phase flag within the blink loop (set = PAUSE text visible).
- Bit 7: re-entry guard; set while "waiting for STOP release", prevents
  a second entry into the blink loop before the key cycles.

The blink loop does **not** call `entity_dispatch` or the scroll update —
the game is fully halted.  The VBlank ISR still fires (E1F8 still increments)
but no game logic executes.

`LAB_4e37` (SELECT+STOP path) calls `sub_5208` and enters the blink loop
without writing the "PAUSE" text first — visually the screen just freezes.
