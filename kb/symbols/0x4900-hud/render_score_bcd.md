---
address: 0x49B5
kind: routine
name: render_score_bcd
confidence: confirmed
inputs:
  HL: pointer to the HIGH byte of a 3-byte BCD value (e.g. 0xE105 = score hi)
  DE: VRAM name-table destination (6 tiles written left→right)
calls:   [0x42ED, BIOS:SETWRT, 0x42F8]
called_by: [0x4996, 0x49A7, 0x49AF, 0x4AA5, 0x49F0, 0x91BD]
sprint: "0047"
tags: [hud, score, video, bcd]
---

# render_score_bcd

## Summary
Render a 3-byte BCD value as **7 tiles** from RAM (`HL` = high byte, read
downward) to the VRAM name table at `DE`: six space-suppressed BCD digits
followed by a literal `'0'`. Scores are therefore stored in units of ten.

## Analysis
Source 0x49B5. `vdp_int_disable`; `EX DE,HL`; `SETWRT(DE)`; `EX DE,HL`; B=3.
Per byte (hi→lo via `DEC HL`): high nibble (`RRCA×4`) then low nibble, each through
the digit helper at **0x49DD** which emits `0x30+digit` for a digit, `0x20` for a
leading zero (D tracks "seen a nonzero digit yet"). Ends writing `0x30` for the
forced final digit, then `vdp_int_enable`.

## Field-width correction (2026-07-30)

This entry previously described a **6**-tile field. The routine writes a
**seventh** tile: after the `B = 3` byte loop ends, 0x49D6–0x49D8 does
`LD A,0x30; OUT (C),A`, pushing a literal `'0'` to the same auto-incrementing
VRAM address.

```
49C1  LD B,0x3          ; 3 bytes = 6 nibbles
49C3  LD D,0x0          ; D = "a nonzero digit has been seen"
49C5 .. 49D2            ; per byte: high nibble then low nibble via 0x49DD
49D6  LD A,0x30         ; <-- the seventh tile, always '0'
49D8  OUT (C),A
```

Suppression applies to all six BCD digits, so a score of 0 renders `"      0"`
(six spaces plus the forced zero) rather than an empty field. This also
reconciles the "7 digits" field widths in [[zanac-vdp-layout]] with the 3-byte
BCD storage, and explains the default top score: `0xE106..0xE108 = 00 10 00`
reads as `001000` + `'0'` → `"  10000"` = 10000, not 1000.

## Live confirmation (sprint 0047)
Micro-exec: score BCD `12 34 56` (E105:E104:E103) rendered **"123456"** to its
VRAM target; `00 00 42` rendered **"    42"** (four leading spaces). All wrapper
entries (0x4996/0x49A7/0x49AF) confirmed below. `tools/sprint0047_verify.py`.
(Those captures read six tiles; the trailing `'0'` sits one cell further on.)
