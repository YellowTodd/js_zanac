---
address: 0x46BC
kind: routine
name: fire_edge_detect
confidence: confirmed
inputs: {}
outputs: { carry: "set on rising edge of any fire key; clear if no rising edge" }
clobbers: [AF, HL]
calls: [0x4343]
called_by: [0x4663, 0x46A8]
tags: [input, fire, edge-detect, keyboard, joystick, e100, e147]
sprint: "0032"
---

# fire_edge_detect

## Summary
Reads keyboard/joystick state via `sub_4343`, then detects a rising edge on
any fire button (SHIFT/SPACE → E100 bit 4; Z/SPACE → E100 bit 5; joystick
port-A triggers → same bits).  Returns carry set only on the first call after
the button is pressed; subsequent calls while held return carry clear.

## Analysis
Source lines 911–925.

```
CALL 0x4343         ; read_keys → E100 updated
LD HL, 0xE147       ; edge-detect latch byte
LD A, (0xE100)
AND 0x30            ; isolate bits 4 and 5 (fire buttons)
CP 0x30             ; both bits 1 (= no fire key pressed)?
BIT 0, (HL)         ; test previous-frame "fire was down" latch
RES 0, (HL)         ; always clear latch
JR C, LAB_46d0      ; carry from CP 0x30 means at least one fire bit = 0
RET                 ; no fire this frame → no carry
LAB_46d0:
SET 0, (HL)         ; fire is down this frame → set latch
RET Z               ; latch was already set (held from last frame) → no carry
CCF                 ; latch was clear (first press) → set carry
RET
```

In E100, fire keys are **active-low** (0 = pressed, 1 = released).
`CP 0x30` sets carry when `(A AND 0x30) < 0x30`, i.e. at least one fire bit
is 0 (at least one fire key is held).

`E147` bit 0 remembers whether fire was down on the previous call.  A rising
edge is detected only when the latch was 0 and fire is now down.  This prevents
a held key from re-triggering continuously.

The same edge-detect output (carry) drives both the game-over skip and the
credits-entry skip in `wait_fire_or_timeout`.  On the title screen,
`title_intro_seq` calls this routine to detect "press fire to start".

Joystick port B triggers (E100 bits 6–7) are **not** tested here (`AND 0x30`
masks them out); only port-A triggers (bits 4–5) advance through this routine.
