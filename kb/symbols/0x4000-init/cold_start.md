---
address: 0x4010
kind: routine
name: cold_start
confidence: confirmed
inputs: {}
outputs: {}
clobbers: [AF, BC, DE, HL, IX, SP]
calls:
  - 0x4E45
  - 0x513F
  - 0x516C
  - 0x428A
  - 0x5A11
  - 0x41DB
  - 0x5BEC
  - 0x42E2
  - 0x5189
called_by:
  - 0x4002
tags: [init, cold-start]
sprint: "0019"
---

# cold_start

## Summary
Cartridge INIT entry point. Pointed to by the ROM header at 0x4002. Performs
full hardware and RAM initialization, installs the VBLANK ISR, runs the intro
animation, then falls into the title-screen loop at `LAB_4042`.

## Analysis (source lines 31–112)

### One-time hardware init (0x4010–0x4041)
1. `DI; IM 1` — disable interrupts, set interrupt mode 1.
2. Install VBLANK ISR: write `0xC3 0xDA 0x43` (JP 0x43DA) at BIOS H_TIMI hook
   (0xFD9A). ISR = `vblank_isr`.
3. `LD SP, 0xF000` — set stack.
4. Clear 0xE700, call `sub_4E45` (ROM/slot mapper setup), call `sub_513F`
   (build PSG frequency table in RAM at 0xF200).
5. `LDIR` clear 0xE000–0xE7FF (2048 bytes) — wipe all game RAM.
6. Set 0xE107 = 0x10 (`topscore_mid` seed → default hi-score 100000), 0xE701 = 1
   (stage/round index → round 1).

### Title-screen loop entry `LAB_4042` (0x4042)
Called on cold boot and re-entered on game-over / attract-mode reset.

1. **`CALL stop_all_sound` (0x516C)** — clear 5 sound slots at 0xE20C,
   reinit PSG via GICINI.
2. **`CALL sub_428A`** — write 8 VDP registers, load charset into VRAM, fill name
   table with spaces, zero entity table at 0xE300.
3. Clear 0xE700.
4. **`CALL title_intro_seq` (0x5A11)** — logo blit + title animation + music start.
5. **`CALL title_screen_init` (0x41DB)** — set up player entity, music pointers,
   one-shot SPACE check, re-fill name table.
6. `LD B, 2; CALL wait_frames` — wait 2 VBLANKs.
7. **`CALL enable_display` (0x42E2)** — screen on.
8. Select music track from 0xE701 bits 0–2; call `play_sound_event` (0x5189).
9. **`CALL sub_5189`** (A = track index) — start title/game music.
10. Enter main entity-dispatch loop at `LAB_4074`.

## Key RAM addresses set during init
| Address | Value | Meaning |
|---------|-------|---------|
| 0xFD9A–0xFD9C | JP 0x43DA | VBLANK ISR hook |
| 0xE107 | 0x10 | `topscore_mid` seed → default hi-score display 100000 |
| 0xE701 | 1    | stage/round index (1 = round 1); main loop reads bits 0–2 to pick music |
| 0xF200 | table | PSG frequency lookup (12 notes × 10 octaves) |
