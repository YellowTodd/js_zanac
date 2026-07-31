---
address: 0x40DA
end: 0x4129
kind: routine
name: level_complete_handler
confidence: confirmed
inputs:
  E722: "next level's stream-start pointer (0 = stay on same stage)"
outputs: {}
clobbers: [AF, BC, DE, HL, IX]
calls: [0x40BA, 0x516C, 0x5189, 0x9444, 0x4177, 0x5BEC, 0x41CB, 0x412A, 0x4163, 0x940C, 0x9AE4, 0x946E, 0x4C4D, 0xBFD6]
called_by: [0x408A]
tags: [main-loop, level-transition, e102, scroll, vram]
sprint: "0034"
---

# level_complete_handler  (LAB_40DA)

## Summary
Runs the stage→stage transition when `E102` bit 5 (`level_complete`) is set:
fade out entities, reload the next level's tiles/stream from `E722`, repaint the
screen, then clear bit 5 and return to the main loop (where bit 3, if also set,
fires the credits). Also the path that loads the ZANAC logo for the ending.

(Canonical `end` is 0x4129; the shared tail `LAB_413A`–`LAB_414D`
(0x413A–0x4162) is documented below but sits after the [[load_bg_level]]
sub-block at 0x412A, which has its own entry.)

## Analysis
Source lines 121–184.
```
CALL 0x40BA            ; reset_entities (fade non-player entities, clear E150/E132)
LD HL,(0xE722)         ; next stream pointer
LD A,H ; OR L ; JP Z,LAB_414D   ; null -> skip reload (same-stage path)
CALL 0x516C            ; stop_all_sound
LD A,0x0B ; CALL 0x5189         ; transition SFX
CALL 0x9444            ; resolve_round_from_ptr: E722 -> round (table at 0x945C); A=new round
PUSH HL ; PUSH AF
CALL 0x445F            ; entity_dispatch (flush one frame)
CALL 0x42ED            ; vdp_int_disable
LD HL,0xE800 ; LD (HL),0 ; LD DE,0xE801 ; LD BC,0x23F ; LDIR   ; clear 0xE800 tile buffer
CALL 0x4177            ; repaint full screen from 0xE800 to the VRAM name table
LD B,0x64 ; CALL 0x5BEC          ; 100-frame fade/wait
CALL 0x42ED
CALL 0x41CB            ; clear per-row status (0xE180), arm E700 bit 0
LD HL,0xE701 ; POP AF ; LD B,(HL) ; LD (HL),A   ; B=old stage, E701=new stage
AND 0x7 ; JR NZ,LAB_413A          ; new stage & 7 != 0 -> normal load
  LD A,B ; AND 7 ; JR Z,LAB_412A   ; old & 7 == 0 too -> LAB_412a (logo path)
  CALL 0x5C60 ; CALL 0x516C ; JR LAB_413A   ; else partial reset
LAB_413A: CALL 0x4163  ; stage-music selector (play_sound_event 1 or 2)
LAB_413D:
  POP HL ; CALL 0x940C ; CALL 0x9AE4 ; CALL 0x946E   ; init stream, sync, build screen
  CALL 0x4177 ; CALL 0x4C4D                            ; repaint VRAM
LAB_414D (0x414D):
  LD HL,0xE102 ; RES 5,(HL)          ; clear level_complete
  LD HL,0xE132 ; A=(HL)+0x20 ; cap at 0xFF ; LD (HL),A   ; advance fade level
  CALL 0xBFD6
  JP 0x4074                          ; back to main loop
```

## Stage-index branch (0x40E2 / 0x411B)
- **`E722 == 0` (0x40E2)**: jump straight to `LAB_414D` — no tile reload (used
  when a sub-event stays on the current stage).
- **new stage & 7 != 0**: normal background load via `LAB_413A` → `sub_4163`.
- **new & 7 == 0 AND old & 7 == 0**: `LAB_412A` ([[load_bg_level]]), which calls
  `load_logo_tiles` — this is how the ending's ZANAC logo gets into VRAM (see
  [[ending_setup]] and sprint 0033).

`sub_4177` (0x4177) is the full-screen blit: it walks the 0x240-byte 0xE800 tile
buffer and writes the Screen-2 name table column-by-column (via 0x8948 + SETWRT).

## Round advance

The `CALL 0x9444` resolves the next round number from the `E722` stream pointer
(see `resolve_round_from_ptr` + `stage_stream_ptr_table`) and writes it to `E701`.
At end of round 8 the scroll engine sets `E722 = 0xA6F4` (ending pointer) and
`E102` bits 5+3; this handler then maps it to `E701 = 0` and clears bit 5,
leaving bit 3 to fire the credits next frame. Full flow: `round-progression.md`.

## Corrections (2026-07-30)

Re-read byte by byte for the web port. The branch skeleton above is right; the
annotations were not.

1. **`sub_4177` is a scattered dissolve, not a column-by-column blit.** 576
   single-cell VDP writes walking `x -= 1` and `y -= 5`, with an extra `y -= 1`
   on every x wrap (net -6). Each of the 24x24 playfield cells is written
   exactly once (period 576); columns 24-31 are never touched. It runs twice -
   at 0x4105 to blank the screen and at 0x4147 to paint the new one - and
   `RES 0,(0xE700)` at 0x417A keeps `scroll_vram_write` out of the way. It
   deserves its own entry.
2. **Type 0x28 is an instant despawn, not a fade.** Its handler is
   0x852C = `JP entity_clear`. That is why 0x40F2 calls `entity_dispatch`
   explicitly: without that pass the retyped slots would still hold their old
   types.
3. **0xE132 is the ALC spawn accumulator** (subsystem I), not a "fade level".
   `reset_entities` zeroes it at 0x40D6 and 0x4156 adds 0x20, so it ends every
   transition at exactly **0x20** and the saturation branch at 0x415B is dead
   on this path.
4. **`resolve_round_from_ptr` (0x9444) does not write 0xE701.** It returns the
   round in `A` and leaves `HL` untouched; the caller stores it at 0x4118.
   (`init_credits_stream` at 0x9439 *does* write it - easy to conflate.)
5. **The 0x412A path skips `restart_round_bgm`**: it jumps to 0x413D, not
   0x413A. Only paths A and B restart the theme.
6. Missing from `calls:`: 0x445F (`entity_dispatch`), 0x42ED
   (`vdp_int_disable`, twice) and 0x5C60 (`load_bg_tiles`). 0x412A is a `JR Z`
   target, not a `CALL`.

### The three tile paths, precisely

`A_new = resolve_round_from_ptr(E722)`, `B_old = E701`, then `E701 = A_new`:

| condition | path | what loads |
|-----------|------|------------|
| `A_new & 7 != 0` | A | **nothing** - rounds 1-7, including every warp between them, reuse the resident tile set. Just [[restart_round_bgm]] |
| else if `B_old & 7 != 0` | B | `load_bg_tiles` (0x5C60) + `stop_all_sound`, then [[restart_round_bgm]] |
| else | C | `stop_all_sound`, `load_charset_sprites`, `load_logo_tiles`, event 0x0A, **no BGM restart** - the 8 -> 0 ending hop |

### Timing that is gameplay, not decoration

The blank hold at 0x410A is **100 frames** (`wait_frames(0x64)`), between the
two dissolves. And 0x413E seeds `0xE702 = trigger - 1` before 0x4144 runs
`map_script_step` **24 times**, so the round's first command batch has already
fired before the first gameplay frame.
