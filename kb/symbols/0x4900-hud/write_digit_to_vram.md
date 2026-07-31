---
address: 0x4B83
kind: routine
name: write_digit_to_vram
confidence: confirmed
inputs:
  A: binary byte 0–99 (2-digit entry 0x4B83) or 0–255 (3-digit entry 0x4B8D)
  HL: VRAM name-table destination
calls:   [BIOS:SETWRT, 0x5BFC]
called_by: [0x4C4D, 0x4C68, 0x4C53]
sprint: "0047"
tags: [hud, video, decimal]
---

# write_digit_to_vram

## Summary
Render a binary byte `A` as **decimal** digit tiles to VRAM, with leading-zero
suppression (suppressed positions become space 0x20). Two entry points:

- **0x4B83** — sets `SETWRT(HL)` then renders **2 digits** (tens + units, 0–99).
- **0x4B8D** — renders **3 digits** (hundreds + tens + units, 0–255); the caller
  must `SETWRT` first. `update_status_bar` jumps here for the lives count.

## Analysis
Source 0x4B83. `PUSH AF; SETWRT(HL); POP AF; LD E,0; JP 0x4BA7` (skip hundreds).
Each digit is computed by repeated subtraction (`SUB 0x64` hundreds, `SUB 0x0A`
tens) giving the count in `C` and remainder in `B`; the digit char is `0x30+n`,
streamed via `vdp_write_byte_di` (0x5BFC). Leading zeros use the `0xF0` trick
(`0xF0+0x30 = 0x20` space) gated by `E` (seen-nonzero flag).

## Live confirmation (sprint 0047)
Micro-exec: 0x4B83 A=42 → "42", A=5 → " 5" (leading space); 0x4B8D A=137 → "137".
`tools/sprint0047_verify.py`.
