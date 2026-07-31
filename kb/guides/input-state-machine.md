---
name: input-state-machine
description: "Complete key/joystick handling for each game state: gameplay, STOP-pause, game-over, and end-credits. E102 flag bit map and per-state input tables."
kind: guide
confidence: confirmed
sprint: "0032"
tags: [input, keyboard, joystick, pause, game-over, credits, e102, state-machine]
---

# Input state machine

## E102 — game-state flag byte

`0xE102` is the central state register read by the main game loop (`LAB_4074`,
0x4074) after every frame.

| Bit | Name | Set by | Cleared by | Effect in main loop |
|-----|------|--------|-----------|---------------------|
| 0 | `player_hit` | collision detection | `sub_4649` | Decrement lives; sets bit 1 or bit 6 |
| 1 | `game_over` | `sub_4649` (lives → 0) | — | `sub_4663`: "GAME OVER" sequence |
| 2 | (scroll flag) | — | `sub_92ca` (RES 2) | Internal scroll engine flag |
| 3 | `end_credits` | scroll engine (`LAB_92af`) | — | `LAB_46d5` → staff-credits sequence |
| 4 | `display_timer` | — | `sub_41ba` (countdown via E15E) | Countdown; clears title state when E15E hits 0 |
| 5 | `level_complete` | scroll engine (`LAB_92af`) | `LAB_414d` (RES 5) | `LAB_40da`: stage transition |
| 6 | `respawn` | `sub_4649` (lives > 0) | main loop (RES 6) | 64-frame scroll loop → `LAB_4068` (reinit player) |
| 7 | `go_to_title` | `sub_4663` (game-over handler) | — | `JP LAB_4042` (title screen) |

Bits 5 and 3 are set together by the scroll engine at `LAB_92af` (end of game).
Bit 5 is processed first; after `LAB_40da` clears it, bit 3 fires the credits
on the next frame.

---

## Active gameplay

Every game frame runs through `sub_9393` (0x9393):

```
sub_9393 (looped B times):
  CALL sub_4306         ; wait one VBlank (sync to 60 fps)
  CALL sub_4da5         ; STOP/SELECT key handler
  CALL sub_4aa5         ; score-display update
  CALL entity_dispatch  ; 0x445F
  CALL sub_4649         ; player-hit handler
```

### Keys active during gameplay

| Key | Source | Effect |
|-----|--------|--------|
| ← / → | row 8 bits 4, 7 → E100 bits 2, 3 | Player X velocity (base 4 ± 3) via E10C |
| ↑ / ↓ | row 8 bits 5, 6 → E100 bits 0, 1 | X velocity ±1 bias |
| SPACE | row 8 bit 0 → E100 bits 4 **and** 5 | Fires both normal shot and fire weapon |
| SHIFT | row 6 bit 0 → E100 bit 4 | Normal shot only (type-2 entity) |
| Z | row 5 bit 7 → E100 bit 5 | Fire weapon only (type-3 entity) |
| Joystick trig A/B (port A) | PSG reg 14 bits 4–5 → E100 bits 4–5 | Equivalent to SHIFT / Z |
| **STOP** (row 7 bit 4) | `sub_4da5` | Enters PAUSE mode (see below) |

---

## STOP key — pause mode (`sub_4da5`, 0x4DA5)

Called every frame from `sub_9393`.  On STOP (row 7, bit 4) press:

1. Checks `E118` bit 7 (re-entry guard); if already in pause, returns.
2. Checks **SELECT** (row 7, bit 6) at the same SNSMAT read:
   - SELECT also held → enters `LAB_4e37` (skips VRAM blink setup).
   - SELECT not held → calls `sub_5208` (mutes sound), writes `"PAUSE"` to
     VRAM at 0x396A (5 bytes), enters blink loop (`LAB_4dd1`).
3. **Blink loop** (`LAB_4dd1`): toggles `"PAUSE"` on/off every 16 frames.
   Does **not** call entity_dispatch or scroll update → **game is fully
   halted** (ISR still runs, VBlank counter E1F8 still increments, but no
   entity or scroll logic executes).
4. `sub_4e0b` re-reads row 7 bit 4 each iteration:
   - STOP released → sets `E118` bit 7 ("waiting for second press").
   - STOP pressed while `E118` bit 7 is set → restore sound, exit with carry
     → `sub_4da5` returns → main loop resumes.

### Keys active in PAUSE state

| Key | Effect |
|-----|--------|
| **STOP again** (row 7 bit 4) | Resume game |
| **SELECT** (row 7 bit 6) | Also resumes (enters `LAB_4e37`, identical outcome) |
| All other keys | **No effect** — not polled inside blink loop |

SELECT without a preceding STOP press has no effect anywhere.

---

## Game-over sequence (`sub_4663`, 0x4663)

Triggered when `E102` bit 1 is set (lives exhausted via `sub_4649`).
Called from the main game loop.

**Exact flow** (confirmed from ROM byte dump):

```
0x4663  Check E102 bit 1; return if clear
0x4669  SET E102 bit 7  (will go to title after this returns)
        sub_40BA    reset entities
        sub_42ED
        sub_4ACE    compare + save high score
        sub_516C    reset PSG / enemies
        LD A, 4
        sub_5189    play sound event 4  (game-over music)
        IY = E180; (IY+C) = 7; (IY+24) = 0x12
        HL = 0x3987
        CALL sub_5c25  ; inline-string write: " GAME OVER \0" → VRAM 0x3987
0x469C  CALL sub_46bc  ; one rising-edge fire check
        BC = 0x320
        CALL sub_46a8  ; wait loop up to 800 frames
0x46A5  JP sub_42f8    ; VBlank enable; return from sub_4663
```

After `sub_4663` returns: E102 bit 7 is set → main loop `JP LAB_4042` → title.

### Keys during game-over

| Key | Effect |
|-----|--------|
| **SPACE / SHIFT / Z** | `sub_46bc` detects rising edge → `sub_46a8` returns carry → exits wait immediately → title |
| **Joystick trigger A/B (port A)** | Same — PSG reg 14 bits 4–5 clear E100 bits 4–5 |
| STOP | `sub_9393` runs inside `sub_46a8` → STOP still pauses |
| All other keys | No effect |

The ~800-frame wait is timed to match the game-over music length; when the
music finishes the wait expires naturally and the game transitions to title.

---

## End-credits sequence (game beaten, `LAB_46d5` / `LAB_46d9`)

Triggered **only** when the game is beaten — the scroll engine sets
`E722 = 0xA6F4` (the ending stream pointer, read by `LAB_40da` at 0x40DD) and
`E102` bits 5 + 3 at `LAB_92af`.  Bit 5 → `LAB_40da` (level-complete
transition) clears it; on the next frame bit 3 → `LAB_46d5` → `LAB_46d9`.
`scripts/credits.tcl` reproduces this trigger (see `ending_setup` symbol).

This is the **staff-credits display**: the background scroll continues
(sub_9393 / sub_9480 run inside `sub_46a8`), and staff names flash in the
screen centre from the table at 0x47AA:

```
GAME DESIGN   (PROGRAM: JANUS / JEMINI)
GRAPHICS      (COMPILE: WAO / MOO / MIYAMOTO / YORIKI)
SOUND         (MUSIC: LUNARIAN)
DIRECTOR      ...
THANKS  PAL
[logo tile graphic]
```

The display loops through entries at 0x4775 (entry control table), with text
strings length-prefixed in the 0x47AA table.

```
LAB_475c:
  sub_46a8(BC)      ; display one entry, wait up to BC frames
  JR C, LAB_475c    ; fire pressed → cycle to next entry, restart timer

  clear_title_state
  sub_46a8(0x50)    ; 80-frame settle
  JR C, →           ; fire during settle → stay
  CALL check_esc_key  ; row 7 bit 2 = ESC
  JP Z, LAB_4042        ; ESC held → title screen
  JP LAB_46e0           ; ESC not held → show credits again from top
```

### Keys during end-credits

| Key | When | Effect |
|-----|------|--------|
| **SPACE / SHIFT / Z / joystick** | During entry display | Cycle to next entry, reset timer |
| **STOP** | Any | Pause still works (via `sub_9393` inside `sub_46a8`) |
| **ESC** (row 7 bit 2) | **After ~8 s of inactivity** | Exit to title screen |
| ESC during active cycling | — | **No effect** |
| Direction keys | — | No effect on credits |

---

## Respawn wait (E102 bit 6)

When the player dies with lives remaining, `sub_4649` sets `E102` bit 6.

1. Main loop clears bit 6.
2. Runs **64 frames** with full `sub_9393` (scroll + entities keep going;
   player slot 0 is inactive).
3. `LAB_4068`: reinitialise entity slot 0 (type=1, flags=0) → rejoin main loop.

STOP key works during the 64-frame respawn wait (sub_9393 → sub_4da5).

---

## State-machine summary

```
Title screen
  ├─ SPACE / SHIFT / Z / joystick (rising edge) → game starts
  └─ ESC held during title_screen_init → continue from last round (E701 retained)

Active gameplay
  ├─ STOP → PAUSE
  │     ├─ STOP again  → resume
  │     └─ SELECT      → resume
  ├─ Player hit → sub_4649
  │     ├─ lives > 0  → 64-frame respawn wait → rejoin
  │     └─ lives = 0  → sub_4663 game-over
  │           ├─ SPACE / SHIFT / Z / joystick → skip to title
  │           └─ 800-frame timeout → title
  └─ Game beaten → credits
        ├─ SPACE / SHIFT / Z / joystick → cycle entry
        └─ ESC (after 8 s idle) → title
```
