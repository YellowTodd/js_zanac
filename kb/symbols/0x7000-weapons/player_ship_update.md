---
address: 0x7612
end: 0x7747
kind: routine
name: player_ship_update
confidence: confirmed
inputs:  { IX: "player entity slot (0xE300)", "(E100)": "input byte", "(E10C)": "x-vel selector" }
outputs: {}
clobbers: [AF, BC, DE, HL, IY]
calls: [0x4343, 0x4cf7, 0xbfab, 0xbfc8, 0x4898]
called_by: [0x75d5]
sprint: "0048"
tags: [player, ship, movement, shot, fire, input]
---

# player_ship_update

## Summary

Per-frame player-ship logic. Polls input ([[read_player_input]] 0x4343), moves
the ship (horizontal via [[xvel_table]] → [[set_velocity_from_dir]], with X/Y
position clamps), handles **shot** firing (E100 bit 4) with the
[[shot_rate_table]] cadence — spawning type-2 [[shot_handler]] entities into the
E320 slot table — and **fire** firing (E100 bit 5) — spawning the type-3
[[fire_weapon_handler]] entity via the E380 control slot — then writes the ship
sprite. Reached by falling through from [[player_ship_handler]] (0x75d5).

## Analysis (0x7612–0x7747)

```
CALL 0x4343                         ; read_player_input -> E100, E10C
LD A,(E10C); CP 4; JP Z,0x7674      ; centred -> no horizontal move
  LD E,A; LD HL,0x7758; ADD HL,DE; LD E,(HL); CALL 0x4cf7  ; xvel_table -> set velocity
; --- apply velocity to position with clamps ---
Y: IX+1/6 += IX+8/9, clamp [0x1e,0xb8]
X: IX+2/7 += IX+0a/0b, clamp [0x28,0xc8]
; --- shot fire (E100 bit 4) + ALC feedback ---
0x767b: bit4 RELEASED? -> E110 = 1 and skip (0x7682)   ; see tap-fire note below
        held: DEC E110; when 0 reload 0x14 (20-frame hold period) and:
  adv = shot_rate_table[E13F-2]  (E13F = fire cadence, frames since last shot)
  E12F += adv ; E131 += adv ; E13F = 0   ; ALC: advance spawn schedule (bfab/bfc8 on carry)
  E141++ (saturating)                     ; ALC fire-event counter
  scan E320 (stride 0x20), only (E10D) slots ([[shot_max_simultaneous]]: 2 or 3
    by shot level) -> free one gets type 0x02, ship X/Y ; spawn shot (0x76d9)
  E140++                                  ; ALC shots-fired counter, on spawn only
; --- fire weapon (E100 bit 5) ---
0x76e9: bit5 held AND E380==0 ? set E380 type=3, copy ship X/Y -> spawn fire entity
; --- spawn-blink + sprite write ---
IX+0x05 bit7 ? toggle attr (IX+4 ^= 0x0e), DEC IX+1b, clear when done
CALL 0x4898; write ship sprite record at (E122) ; RET
```

`E380` is the fire-weapon control slot ([[fire_select]] also forces E380=3 for
fire 2). **E13F is the fire *cadence* counter (frames between shots), not auto-fire
spacing** — spacing is the fixed 20-frame E110 period. The cadence→advance lookup
([[shot_rate_table]]) is the primary **ALC** feedback: it accelerates the spawn
schedule the more aggressively the player fires. See [[alc-adaptive-difficulty]].

## Tap-fire is faster than holding (0x7682, noted 2026-07-30)

Every frame the button is **released**, 0x7682 stomps `E110 = 1` — so the next
press decrements 1→0 and fires **immediately**, then reloads 0x14. Holding
therefore fires once per 20 frames, but tapping fires on every press (bounded
only by the (E10D) in-flight cap). This is Zanac's signature rapid-fire
technique, and it is load-bearing for the game balance: a totem (HP 6) crosses
the screen in ~115 frames, so the ~5.75 shots a pure hold delivers can never
pop one — the design assumes tapping. Also note the 0x768F reload and the ALC
bookkeeping (E13F reset, E141++) run on every expiry even when the slot scan
then finds no free slot; only `E140++` is spawn-gated (0x76E8).

## Confirmed (sprint 0048)

Live: steering changed X (E302) and Y (E301) in the expected directions
(right→200, left→112, up→67); holding shot reached the spawn write 0x76d9
repeatedly. `tools/sprint0048_live.py`.
