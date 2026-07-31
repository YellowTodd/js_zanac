---
address: 0x91FD
end: 0x92C9
kind: routine
name: ending_setup
confidence: confirmed
inputs:
  A: "ending sub-event selector (post `SUB 0xf` at 0x91EA: 1=LAB_91fd, 2=letters, >=3=LAB_92af)"
  IX: "0xE100 (game-state base; see the 2026-07-30 correction)"
outputs: {}
clobbers: [AF, BC, DE, HL]
calls: [0x516C, 0x42ED, 0x005C, 0x9433, 0x946E, 0x0059, 0x5189, 0x9393, 0x92CA]
called_by: [0x91EF]
tags: [credits, ending, scroll, vram, logo, audio]
sprint: "0033"
---

# ending_setup  (LAB_91fd / LAB_92af)

## Summary
The two scroll-engine ending sub-events the game runs after the final boss
dies. `LAB_91fd` (0x91FD) loads ending music and pre-builds the credits/logo
tile screen; `LAB_92af` (0x92AF) arms the staff-credits display. Reached from
the ending dispatcher (0x91A6–0x91EF) keyed on `(IX+0x57) & 0x1f`.

`scripts/credits.tcl` reproduces **LAB_92af** to trigger the ending on demand
— see "Triggering from anywhere" below.

## LAB_91fd (0x91FD) — annotated (answers to sprint 0033 questions)
```
CALL 0x516C            ; (Q6) stop_all_sound: zero the 5 sound slots at
                       ;      0xE20C + GICINI -> mutes PSG, stops enemy fire.
CALL 0x42ED            ; vdp_int_disable
LD HL,0xE800 / DE,0x3C00 / BC,0x240
CALL 0x005C            ; (Q1) LDIRVM (RAM->VRAM): stash the live 24x24 tile
                       ;      screen (0xE800) into VRAM scratch at 0x3C00.
LD HL,0xBBB4
CALL 0x9433            ; (Q2) init the level-stream engine onto the credits
                       ;      tile data at 0xBBB4 (sub_9444 -> stage idx E701;
                       ;      0x941b sets E702/E704/E706). Streams tiles; does
                       ;      NOT itself blit VRAM pattern data.
CALL 0x946E            ; (Q3) sub_946e: 24x sub_94c3 -> builds the full credits
                       ;      24x24 tile screen into 0xE800.
LD HL,0xE800 / DE,0xEB00 / BC,0x240 / LDIR   ; copy credits screen -> 0xEB00.
LD HL,0x3C00 / DE,0xE800 / BC,0x240
CALL 0x0059            ; (Q1/Q7) LDIRMV (VRAM->RAM): restore the stashed live
                       ;      screen from 0x3C00 back into 0xE800.
LD (IX+0x57),0xD1      ; (Q8) IX=0xE700; 0x57/0x56/0x50 are scroll_state fields.
LD (IX+0x56),0x0C      ;      0x57=ending-phase index (0xD1&0x1f=0x11 -> next
LD (IX+0x50),0x01      ;      dispatch phase). 0x56/0x50 = phase sub-state.
LD (0xE700),0x0C       ; (Q4) E700 bits 2+3 for the logo-reveal phase:
                       ;      bit3 -> sub_94c3 syncs each column to VBLANK via
                       ;      sub_9ae4 (0x94C3); bit2 -> alternate end path
                       ;      JP 0x980e (logo reveal, copy_tile_column 0x986E).
LD (0xE710),0x20       ; (Q5) current_scroll_speed seed for the reveal phase
                       ;      (scroll accumulator, see scroll_velocity_ctrl).
LD A,0x0C / CALL 0x5189 ;     play_sound_event(0x0C) — ending music.
JP 0x92CA              ; sub_92ca: RES E102 bit 2; RET.
```

**Net effect of the stash/restore dance (Q1+Q7):** VRAM 0x3C00 is used as
temporary storage so the credits screen can be assembled into 0xEB00 (by
sub_9433/946e) *without* disturbing the live 0xE800 screen. 0xEB00 is then
revealed column-by-column into 0xE800 by [[copy_tile_column]] during the
E700=0x0C reveal phase.

## LAB_92af (0x92AF) — arms the credits display
```
LD HL,0xA6F4 / LD (0xE722),HL   ; ending level-stream pointer (round-0 data).
SET 5,(0xE102)                  ; level_complete -> main loop dispatches LAB_40da.
SET 3,(0xE102)                  ; end_credits    -> then LAB_46d5 display loop.
LD B,0x3C / CALL 0x9393         ; 60 transition frames (smooth hand-off).
LD (0xE700),0x00                ; scroll engine back to default mode.
LD (0xE712),0x80                ; target scroll speed = fast ("game beaten").
; falls into sub_92ca: RES E102 bit 2; RET.
```

## Where the ZANAC logo pixels come from
`LAB_91fd`/`copy_tile_column` only move tile **codes**. The logo **pixel
patterns** are decompressed into VRAM PGT tiles 176–236 by `load_logo_tiles`
(0x5C3C) — the *same* routine the title screen uses. In the real ending it is
reached because `LAB_92af`'s bit-5 fires `LAB_40da`, which reloads the stream
from `E722` (round 0 -> new stage & 7 == 0) and, when the **old** stage is also
a multiple of 8 (it transitioned from round 8), branches to `LAB_412a` which
calls `load_logo_tiles`. See `kb/guides/input-state-machine.md` §end-credits.

## Triggering from anywhere (scripts/credits.tcl)
Setting only `E102` bit 3 (old credits.tcl) renders the logo as a garbled
multicolour block because `load_logo_tiles` never runs. The working trigger
reproduces `LAB_92af` **and** forces the old stage to a multiple of 8:

| Write | Why |
|-------|-----|
| `E701 = 0x00` | old stage & 7 == 0 so `LAB_412a` -> `load_logo_tiles` runs |
| `E722 = 0xA6F4` | ending stream (round 0); read by `LAB_40da` at 0x40DD |
| `E712 = 0x80` | fast scroll target |
| `E700 = 0x00` | default scroll mode |
| `E102 \|= 0x28`, `&= ~0x04` | set bit 5 + bit 3, clear bit 2 (= `LAB_92af`) |

Verified against `savestates/game-end.oms` by screenshot (sprint 0033): fade to
black, fast round-0 terrain scroll, controllable player ship, ending music,
flashing developer names, and the clean ZANAC logo.

## Correction (2026-07-30): IX is 0xE100, and that is the chaining mechanism

The annotation above reads the 0x9231-0x9239 writes as scroll-state fields
with `IX = 0xE700`. The ceremony runs inside [[base_tick]], where **IX =
0xE100**, so they are:

| write | actually | effect |
|-------|----------|--------|
| `(IX+0x57) = 0xD1` | **0xE157 scenario** | next ending beat (kind 0x11) |
| `(IX+0x56) = 0x0C` | **0xE156 approach** | 12 approach steps before it re-opens |
| `(IX+0x50) = 0x01` | **0xE150 = armed** | the base machine runs again with no segments |

That is how the finale chains: each beat re-arms the (empty) base with the
next scenario, the ceremony fires again, and the dispatcher at 0x91EA picks
the next beat — 0xF0 (logo build + column reveal + music 0x0C) → 0xD1 (the
0x9254 letter rows from 0xBBFD with explosion bursts, then the 0xBBF3 splice
and scenario 0xB2) → 0xB2 (LAB_92AF arms the credits). The absolute writes to
0xE700/0xE710 in the same block *are* scroll fields, which is what made the
IX slip easy to miss.
