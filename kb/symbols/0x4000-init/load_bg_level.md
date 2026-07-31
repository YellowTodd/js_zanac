---
address: 0x412A
end: 0x4139
kind: routine
name: load_bg_level
confidence: likely
inputs: {}
outputs: {}
clobbers: [AF, BC, DE, HL]
calls: [0x516C, 0x5CA5, 0x5C3C, 0x5189]
called_by: [0x4120]
tags: [level-transition, graphics, vram, logo]
sprint: "0034"
---

# load_bg_level  (LAB_412A)

## Summary
The "stage is a multiple of 8" level-load path inside
[[level_complete_handler]]. Reached only when **both** the old and new stage
indices are `& 7 == 0` (i.e. round 0 / round 8). Loads the background tile set
**and the ZANAC logo**, then plays the stage-0 music.

## Analysis
Source lines 157–163.
```
CALL 0x516C   ; stop_all_sound
CALL 0x5CA5   ; load background tile set / palette for the stage (decompressor)
CALL 0x5C3C   ; load_logo_tiles — decompress the ZANAC logo into VRAM PGT 176-236
LD A,0x0A ; CALL 0x5189   ; play_sound_event(0x0A) — stage-0 music
JR LAB_413D   ; rejoin level_complete_handler (stream init + VRAM repaint)
```

## Why it matters
This is the only routine that calls `load_logo_tiles` (0x5C3C) outside the title
screen. The end-credits trigger (`scripts/credits.tcl`, sprint 0033) deliberately
forces `E701 = 0` so the old-stage test at 0x411B passes and this path runs —
otherwise the credits logo renders as garbage. `0x5CA5` is the background-tile
loader (decompresses the stage tile/colour data into VRAM); `confidence: likely`
pending a dedicated decode of 0x5CA5.
