---
address: 0x4C74
end: 0x4C8A
kind: routine
name: render_hex_byte
confidence: confirmed
inputs:
  A: byte to render
  VRAM write pointer: must be pre-set by the caller (SETWRT)
outputs: {}
clobbers: [AF]
calls:   [0x5BFC]
called_by: [0x9082, 0xBFE9, 0xBFEF, 0xBFF5]
sprint: "0047"
tags: [hud, video, hex, alc]
---

# render_hex_byte

## Summary
Render a byte `A` as **two hexadecimal digit tiles** (0–9, A–F) to the current
VRAM write address. Used to display multi-byte counters in hex — notably the
**ALC** value (rendered by 3 back-to-back calls at 0xBFE9/0xBFEF/0xBFF5 →
6 hex digits) and a value at 0x9082 (scroll engine).

## Analysis
Source 0x4C74:
```
4C74  PUSH AF; RRCA×4; CALL 0x4C7D   ; high nibble
4C7C  POP AF
4C7D  AND 0x0F; ADD A,0x30           ; nibble → '0'..'9'
4C81  CP 0x3A; JP C,0x5BFC           ; <= '9' → write
4C86  ADD A,0x07; JP 0x5BFC          ; else +7 → 'A'..'F'
```
Each nibble is streamed via `vdp_write_byte_di` (0x5BFC); the caller sets the
VRAM address first (it does not `SETWRT`).

## Live confirmation (sprint 0047)
Micro-exec (after `SETWRT`): A=0xAB → "AB", 0x3C → "3C", 0x07 → "07".
`tools/sprint0047_verify.py`.

## See also
- `write_digit_to_vram.md` — the decimal counterpart.
- ALC display at 0xBFE9–0xBFF5 (subsystem I) — primary consumer.
