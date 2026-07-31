---
address: 0x4663
kind: routine
name: game_over_handler
confidence: confirmed
inputs: {}
outputs: {}
clobbers: [AF, BC, DE, HL, IY]
calls: [0x40BA, 0x42ED, 0x4ACE, 0x516C, 0x5189, 0x5C25, 0x46BC, 0x46A8, 0x42F8]
called_by: []
tags: [game-over, e102, hiscore, music, vram]
sprint: "0032"
---

# game_over_handler

## Summary
Handles the game-over sequence: saves the high score, plays the game-over
jingle, writes "GAME OVER" to VRAM, then waits up to 800 frames (or until the
player presses fire) before returning to the title screen.

## Analysis
Source lines 866–897.

```
LD HL, 0xE102
BIT 1, (HL)         ; game_over flag set?
RET Z               ; no — nothing to do
SET 7, (HL)         ; set go_to_title flag immediately
CALL 0x40BA         ; reset_entities
CALL 0x42ED         ; vdp_int_disable
CALL 0x4ACE         ; compare_save_hiscore (E103 vs E106, 3 bytes BCD)
POP HL              ; (HL was pushed before CALL 0x42ED)
CALL 0x516C         ; stop_all_sound
LD A, 4
CALL 0x5189         ; play_sound_event(4) — game-over music
LD IY, 0xE180
LD (IY+0x0C), 7
LD (IY+0x24), 0x12
LD HL, 0x3987
CALL 0x5C25         ; inline-string write " GAME OVER \0" → VRAM 0x3987
; inline string bytes at 0x4692–0x469B follow the CALL in ROM;
; sub_5c25 reads them and resumes at LAB_469c (0x469C)
LAB_469c:
CALL 0x46BC         ; fire_edge_detect — arm edge detector for fire key
LD BC, 0x320        ; 800 decimal
CALL 0x46A8         ; wait_fire_or_timeout(BC=800)
JP 0x42F8           ; vdp_int_enable → return
```

`E102` bit 7 (`go_to_title`) is set before any heavy work so the main loop
will redirect to title even if something returns early.

`sub_5c25` uses an inline-string convention: the null-terminated string lives
in ROM immediately after the `CALL` instruction and `sub_5c25` advances the
return address past it.

The `wait_fire_or_timeout` wait of 800 frames (~13 s at 60 fps) matches the
game-over music length.  Pressing SPACE/SHIFT/Z/joystick skips directly to
title without waiting for music.

After this routine returns, the main loop sees E102 bit 7 and jumps to title.
