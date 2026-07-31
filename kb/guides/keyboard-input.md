---
name: keyboard-input
description: "MSX keyboard and joystick input handling: E100 state byte layout, all mapped keys, title-screen start conditions, and the ESC continue"
kind: guide
confidence: confirmed
sprint: "0019"
tags: [input, keyboard, joystick, psg, title-screen]
---

# Keyboard and joystick input

## Input reader: `sub_4343` (0x4343)

Called every frame via `sub_46bc` (0x46BC) and directly from the main game
loop.  Builds a single **input state byte at 0xE100** from two sources:

### 1 — Joystick (PSG register 14)

```
WRTPSG reg 15, 0x8F   ; select port A as input
RDPSG reg 14   → A    ; read port A directions + triggers
LD (E100), A          ; store raw joystick value

WRTPSG reg 15, 0xCF   ; select port B
RDPSG reg 14   → A    ; read port B
AND (E100)            ; combine both ports (active-low AND)
LD (E100), A          ; write back
```

PSG reg 14 bit layout (active-low: 0 = pressed):

| Bit | Port A | Port B |
|-----|--------|--------|
| 0 | UP | — |
| 1 | DOWN | — |
| 2 | LEFT | — |
| 3 | RIGHT | — |
| 4 | Trigger A | Trigger A |
| 5 | Trigger B | Trigger B |
| 6–7 | (port B triggers land here after second AND) | — |

E100 bits 6–7 reflect joystick port B triggers from the PSG reads and are
**not overwritten by any keyboard mapping**.

### 2 — Keyboard (SNSMAT rows 8, 6, 5)

After the PSG read, individual bits in E100 are **cleared** (active-low) when
the corresponding key is pressed:

| SNSMAT row | Bit tested | Key | Clears E100 bit(s) |
|------------|-----------|-----|-------------------|
| Row 8 | bit 0 | SPACE | bits **4 and 5** |
| Row 8 | bit 5 | ↑ UP | bit **0** |
| Row 8 | bit 6 | ↓ DOWN | bit **1** |
| Row 8 | bit 4 | ← LEFT | bit **2** |
| Row 8 | bit 7 | → RIGHT | bit **3** |
| Row 6 | bit 0 | SHIFT | bit **4** |
| Row 5 | bit 7 | Z | bit **5** |

### E100 final bit layout

| Bit | Meaning | Cleared by |
|-----|---------|-----------|
| 0 | UP direction | ↑ key |
| 1 | DOWN direction | ↓ key |
| 2 | LEFT direction | ← key |
| 3 | RIGHT direction | → key |
| 4 | Shot / fire (weapon A) | SPACE **or** SHIFT |
| 5 | Fire weapon (weapon B) | SPACE **or** Z |
| 6 | Joystick B trig A | joystick B button A |
| 7 | Joystick B trig B | joystick B button B |

`sub_4343` then computes **E10C** (player X-velocity) from bits 0–3:
base value 4, +1 for UP, −1 for DOWN, −3 for LEFT, +3 for RIGHT.

---

## Edge-detection: `sub_46bc` (0x46BC)

Wraps `sub_4343` and provides a **rising-edge** fire detector used on the
title screen and during game-over transitions.

```
AND (E100), 0x30   ; isolate bits 4 and 5
CP  0x30           ; carry if at least one fire bit is clear (button pressed)
BIT 0, (E147)      ; test previous-frame fire state
RES 0, (E147)      ; clear it
JR  C, pressed     ; jump if fire detected this frame
RET                ; no fire → return NC

pressed:
SET 0, (E147)      ; record pressed state
RET Z              ; if E147.bit0 was 0 (just became pressed) → return C=1
CCF                ;    else (was already pressed) → return C=0
RET
```

**Returns carry set only on the first frame the button is pressed.**  If a
button is held from a previous screen, the first call to `sub_46bc` arms
E147.bit0, and subsequent calls while held return NC — preventing accidental
skip of the title animation.

---

## Title screen: all keys that start the game

`sub_46bc` is polled in the `title_intro_seq` (0x5A11) animation loop:

```
call sub_46bc
ret  C          ; C=1 → leave title screen, enter title_screen_init
```

**Any of the following pressed fresh (rising edge) starts the game:**

| Key | E100 bit cleared |
|-----|-----------------|
| SPACE (row 8 bit 0) | bits 4 **and** 5 |
| SHIFT (row 6 bit 0) | bit 4 only |
| Z (row 5 bit 7) | bit 5 only |
| Joystick port A — trigger A | bit 4 |
| Joystick port A — trigger B | bit 5 |
| Joystick port B — trigger A/B | bits 6–7 (also causes CP to see < 0x30) |

---

## title_screen_init: ESC = continue from last round

`check_esc_key` (0x43D2) is called **once** during `title_screen_init`
(0x41DB) immediately after the player has pressed a start key:

```
LD  A, 7
CALL SNSMAT     ; read keyboard row 7
BIT 2, A        ; test bit 2 = ESC key (row 7 col 2)
RET             ; returns Z=1 if ESC pressed, Z=0 otherwise
```

**Row 7 bit 2 = ESC** (confirmed from openMSX unicodemap `jp_ansi` / `int`;
the earlier sprint-0017 note "JP SPACE" was incorrect).

### The continue mechanism

Cold-start (0x4010) initialises E701=1 **once** (line 56), then jumps to
`LAB_4042`.  The game-over return path also enters `LAB_4042` **without
resetting E701**, so E701 retains whatever round was reached during the last
play session.

`title_screen_init` then branches on the ESC check:

```z80
CALL check_esc_key    ; Z=1 if ESC held
PUSH AF
CALL sub_428a           ; screen init (PUSH/POP preserves Z)
POP  AF
JR   Z, LAB_425a        ; ESC held → skip the write below
LD   (IX+1), 0x1        ; ESC not held → E701 = 1  (round 1)
LAB_425a:
LD   A, 0x8
SUB  (IX+1)             ; A = 8 − E701  →  level-table index
```

| ESC at title screen | Effect on E701 | Starts at |
|---------------------|---------------|-----------|
| not held (normal) | **reset to 1** | round 1 always |
| **held** | **unchanged** (last gameplay value) | **last round reached** |

**On a cold boot** E701 is already 1, so ESC+SPACE and plain SPACE are
identical.  The continue effect only activates when the player has completed
at least one session in the same power cycle.

Round 0 is reachable via continue only if a prior life left **E701 = 0**. That
happens at the round-8 → ending transition, and also via an in-game **warp orb**
whose destination resolves below round 1 (some idol sub-types randomise the orb's
`+0x1C` → round 0). Round 0 is a real playable stage (stream 0xA65C) whose tail
segment is reused for the ending. The warp orb is real — shoot a ground idol,
let its orb turn black, touch it; see **[[idol-warp-orbs]]** and
[[M-secrets-and-warps]] (live-confirmed, sprints 0058/0059).

### Level-start table (0x945C)

| E701 | Round | Level start addr |
|------|-------|-----------------|
| 0 | 0 (secret) | 0xA65C |
| 1 | 1 (normal) | 0xA751 |
| 2 | 2 | 0xAAEF |
| 3 | 3 | 0xAD61 |
| 4 | 4 | 0xAF1F |
| 5 | 5 | 0xB1DE |
| 6 | 6 | 0xB3FD |
| 7 | 7 | 0xB61A |
| 8 | 8 (final) | 0xB7A5 |

The `warp` command in `scripts/warp.tcl` exploits this by patching E701 at
`0x425A` (the instruction that reads E701 to compute the table index).

---

## Debounce variable E147

`0xE147` bit 0: set when a fire button is pressed, cleared on the next call to
`sub_46bc` that reads no fire.  Acts as a one-frame memory so that `sub_46bc`
only returns carry on the **transition** from not-pressed to pressed.
