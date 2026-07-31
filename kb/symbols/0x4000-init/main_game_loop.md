---
address: 0x4042
end: 0x40B9
kind: routine
name: main_game_loop
confidence: confirmed
inputs: {}
outputs: {}
clobbers: [AF, BC, DE, HL, IX]
calls: [0x516C, 0x5A11, 0x41DB, 0x9480, 0x8F5E, 0x9393, 0x4663, 0xBF2C, 0x40DA, 0x46D5, 0x41BA]
called_by: [0x4094, 0x4174, 0x40B7]
tags: [main-loop, dispatch, e102, state-machine]
sprint: "0034"
---

# main_game_loop  (LAB_4042 + LAB_4074)

## Summary
The top-level per-frame game loop. `LAB_4042` (0x4042) is the title-restart
entry that (re)initialises a game and falls into `LAB_4074` (0x4074), the frame
dispatcher that runs one frame of each subsystem then branches on `E102`.

## LAB_4042 (0x4042) — restart / new game
Source lines 54–74.
```
CALL 0x516C            ; stop_all_sound (mute PSG, clear sound slots)
CALL 0x428A            ; (VDP/display setup)
SUB A ; LD (0xE700),A  ; clear scroll_flags
CALL 0x5A11            ; title_intro_seq (title screen: logo + music)
CALL 0x41DB            ; full game/player/level init (0x41DB)
LD B,2 ; CALL 0x5BEC   ; wait 2 frames
CALL 0x42E2            ; enable display
LD A,(0xE701); AND 7   ; stage & 7 -> pick music track
LD A,7 ; JR NZ,4065 ; LD A,2     ; track 7 (normal) or 2 (stage 0/8)
CALL 0x5189            ; play_sound_event(track)
LAB_4068 (0x4068):     ; (re)init player entity slot 0
LD IX,0xE300 ; (IX+0)=1 ; (IX+5)=0
; falls into LAB_4074
```
`LAB_4068` is the **respawn re-entry** target: after a death the loop jumps here
to reactivate the player without re-running the full init.

## LAB_4074 (0x4074) — per-frame dispatch
Source lines 75–104.
```
CALL 0x9480   ; scroll_velocity_ctrl  (scroll pre-compute)
CALL 0x8F5E   ; sub_8f5e: base/boss encounter scroll-mode + speed ramp (see below)
LD B,1 ; CALL 0x9393   ; gameplay_frame_loop x1 (vblank sync, entities, player hit)
CALL 0x4663   ; game_over_handler (HUD/score + GAME OVER sequencing)
CALL 0xBF2C   ; sub_bf2c: timed spawn-script ticker (see below)
LD A,(0xE102)         ; --- branch on game-state flags ---
BIT 5 -> JP 0x40DA    ; level_complete  -> level_complete_handler
BIT 3 -> JP 0x46D5    ; end_credits     -> staff-credits display
BIT 7 -> JP 0x4042    ; go_to_title     -> restart at LAB_4042
BIT 4 -> CALL NZ 0x41BA   ; display_timer  -> display_timer_countdown
BIT 6 -> if 0: JP 0x4074  ; no respawn pending: next frame
         else RES 6, run LAB_40A8 x0x40 (64 frames), JP 0x4068   ; respawn wait
```
See `kb/guides/input-state-machine.md` for the full E102 bit map.

### Respawn loop (LAB_40A8, 0x40A8)
When `E102` bit 6 is set (`sub_4649`, player died with lives left): clear bit 6,
then run 64 frames of `scroll_velocity_ctrl` + `sub_8f5e` + `gameplay_frame_loop`
(scroll and enemies keep moving, player absent), then `JP 0x4068` to revive the
player.

## Key-question answers
- **sub_8f5e (0x8F5E)** — *not* the tile pipeline. It is the base/boss
  **encounter scroll-mode controller**: dispatches on `E150`
  (`base_encounter_flags`) to 0x934D / 0x9028, and ramps `E710`
  (current_scroll_speed) up through the table at 0x8F9A
  (`0C 11 14 17 1A 1D 20 23 26`) as a structure/boss is approached. The per-frame
  tile pipeline lives in `gameplay_frame_loop` (sub_9393) and the VBLANK ISR
  ([[scroll_vram_write]]).
- **sub_bf2c (0xBF2C)** — the **timed spawn-script ticker**: advances the spawn
  countdown timers at E137/E138, indexes the spawn table at `(0xE133)` by the
  counter `(IX+0x26)`, and spawns each due entity via 0x4496. Returns early if
  `E102` bit 3 (end_credits) is set.

## Note on naming
This entry covers what sprint 0034 listed as `title_restart` — the routine is
the main loop, so it is named accordingly.
