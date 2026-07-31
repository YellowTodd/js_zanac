---
address: 0x946E
end: 0x947F
kind: routine
name: build_tile_screen
confidence: likely
inputs:
  IX: "set internally to 0xE700 (scroll_state)"
outputs: {}
clobbers: [AF, BC, DE, HL]
calls: [0x94C3]
called_by: [0x9219, 0x4144]
tags: [scroll, tile, ending, credits]
sprint: "0033"
---

# build_tile_screen  (sub_946e)

## Summary
Runs the per-column scroll tile reader (`sub_94c3`) **24 times** to assemble a
complete 24×24 tile screen into the 0xE800 buffer in one shot, without waiting
for per-frame scrolling. Used after [[init_credits_stream]] to materialise the
credits/logo screen, and by `LAB_40da` (0x4144) when reloading a level.

## Analysis
Source lines 7225–7235.
```
PUSH IX
LD IX, 0xE700          ; scroll_state base
LD B, 0x18             ; 24 columns
loop (LAB_9476):
    PUSH BC ; CALL 0x94C3 ; POP BC     ; sub_94c3: read+place one tile column
    DJNZ loop
POP IX ; RET
```
`sub_94c3` (0x94C3) is the [[map_script_step]] interpreter: it advances the map
row counter (E702), runs the map-script command parser when the row trigger
(E706) is reached, and otherwise writes the next tile column into the 0xE800
buffer. Calling it 24× fills the whole visible buffer in one shot. (It is also
the fall-through tail of [[scroll_velocity_ctrl]], which enters it per frame
once the speed accumulator carries.)
