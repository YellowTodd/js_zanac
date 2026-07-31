---
address: 0x41DB
end: 0x4289
kind: routine
name: title_screen_init
confidence: confirmed
inputs: {}
outputs: {}
clobbers: [AF, BC, DE, HL, IX]
calls:
  - 0x42D7
  - 0x516C
  - 0x41CB
  - 0x42ED
  - 0x43D2
  - 0x428A
called_by: [0x4042]
tags: [init, title-screen]
sprint: "0041"
---

# title_screen_init

## Summary
Sets up all game state for the title-screen loop: initialises the player entity
at 0xE100, clears the display state buffer, stores music-data pointers, runs
the VDP in disabled state, performs a one-shot SPACE-key check, and then fills
the name table (via `sub_428A`). Called once per title-screen entry from
`LAB_4042`.

## Sequence (source lines 261–352)

1. **`CALL disable_display` (0x42D7)** — screen off before touching VRAM.
2. **`CALL stop_all_sound` (0x516C)** — clear 5 sound-engine slots at 0xE20C,
   reinitialize PSG via GICINI.
3. **Entity setup (IX=0xE100)** — writes ~15 offsets into the player entity slot:
   type byte, spawn coords (E103–E104), health, animation index, etc. See game_state_block.
4. **`CALL clear_title_state` (0x41CB)** — zeroes 0xE180–0xE1AF, sets 0xE700 bit 0.
5. **Music-data pointers**: stores ROM addresses 0xA624 and 0xA63C into 0xE2B4/0xE2B6.
6. **0xE700 = 0; 0xE712 = 0x34** — clear DMA trigger, set initial title-state byte.
7. **`CALL vdp_int_disable` (0x42ED)** — prevent ISR during the ESC read.
8. **`CALL check_esc_key` (0x43D2)** — ONE-SHOT read of keyboard **row 7 bit 2
   (ESC)**. Returns Z=1 if ESC is held. The Z flag is saved across the next call
   via `PUSH AF` (0x424F) / `POP AF` (0x4253). The *start* key (SPACE/SHIFT/Z)
   is detected separately by the logo loop in `sub_5A11` via `sub_46bc`.
9. **`CALL sub_428A`** — fills name table at VRAM 0x3800 with 0x20 (spaces),
   clears sprite Y-table at 0x3B80, zeroes entity table at 0xE300.
10. **`JR Z,0x425A`** (0x4254): if ESC was **not** held (Z=0) → `LD (IX+1),1`
    sets **0xE701 = 1** (round 1). If ESC **was** held (Z=1) → skip the write, so
    E701 keeps its current value → the game **continues from the last round**
    (the secret round 0 is reached this way if a prior warp death left E701=0).
    Either way, `A = 8 − E701` (0x425A–0x425C) then indexes the level table.

## Key addresses set here
| Address | Value | Meaning |
|---------|-------|---------|
| 0xE2B4  | 0xA624 | music data pointer A (title track) |
| 0xE2B6  | 0xA63C | music data pointer B (title track) |
| 0xE700  | 0     | DMA trigger cleared |
| 0xE712  | 0x34  | title state byte |
| 0xE701  | 1 (only if ESC **not** held) | round/level selector (`8 − E701` = level-table index) |

## Notes
- The ESC check here is the **continue/secret** modifier, distinct from the
  start-key detection in the logo loop `title_intro_seq` (0x5A11), which calls
  `sub_46bc` every frame for joystick/SPACE/SHIFT/Z. Holding ESC while starting
  preserves the last round (see [[M-secrets-and-warps]]); `scripts/warp.tcl`
  patches E701 at 0x425A.
- Music-data pointers at 0xA624/0xA63C are used by the sound engine (sprint 0020).
