---
address: 0x5CCF
end: 0x5D01
kind: routine
name: decompress_block
confidence: confirmed
inputs:
  DE: ROM source address of one compressed block
  HL: VRAM destination base address
  BC: VRAM section stride (always 0x800 = 2048 bytes)
outputs: {}
clobbers: [AF, BC, DE, HL]
calls:   [0x0053, 0x5C07, 0x5D1A, 0x5C2E]
called_by: [0x5C3C, 0x5C60, 0x5CA5]
tags: [graphics, rle, vram]
sprint: "0007"
---

# decompress_block

## Summary
Single-block RLE decompressor. Decodes one compressed data block from ROM into
VRAM, then returns. The stop-handler **restores the original DE and HL** on exit,
so callers can re-pass the same ROM address to decompress the same block to a
different VRAM section (used to replicate tile data across all 3 Screen-2 thirds).

## Algorithm (from `xtra/zanac-decoder.py`)

State: `special` = current escape byte (init 0xFF); `mode` ∈ {copy, repeat}.

Main loop reads one ROM byte at a time:
- **Normal byte** (≠ special): call `sub_5d1a`.
  - Copy mode: write byte directly to VRAM via OUT port (sub_5c07).
  - Repeat mode: read count byte, write `count` copies via OUT.
- **Single special**: toggle mode (copy ↔ repeat); no VRAM output.
- **Double special + 0x00** → **STOP**: restore registers, return.
- **Double special + 0x01 + X** → **SET SPECIAL**: change escape byte to X.
- **Double special + 0x02 + M + N** → **MULTI**: re-process the next N
  copy/repeat units M times from the same ROM position (outer loop repeats
  the inner block M times). Used for the three-section Screen-2 tile mirrors.

## Analysis
Source lines 2044–2100 (decoded); handler table at 0x5CF8:
- Command 0 (STOP): handler at 0x5CFE (POP HL; POP DE; POP BC; RET).
- Command 1 (SET SPECIAL): handler at 0x5D02 (LD D,(HL); INC HL; JP LAB_5cdd).
- Command 2 (MULTI): handler at 0x5D06 (outer/inner DJNZ loops; JP LAB_5cdd).

Entry sequence:
1. SUB A → A=0; PUSH BC, DE, HL, AF.
2. CALL WRTVRM — sets VDP write address to HL and writes one 0x00 byte.
3. EX DE, HL — HL now = ROM source, VDP write address auto-increments from HL+1.
4. Decode loop reads from HL, outputs to VDP data port (sub_5c07) until stop.
5. STOP handler: POP HL (orig VRAM addr), POP DE (orig ROM addr), POP BC, RET.

**Key property**: because the STOP handler restores original DE and HL, the
same compressed block can be decoded to three consecutive VRAM sections by
calling this routine three times with the same DE and HL += 0x800 each time.

## Decompressor helpers
- [[decompress_unit]] (0x5D1A): handle one normal ROM byte (copy once, or repeat
  N times reading a count byte) via [[vdp_write_byte]].
- [[vdp_write_byte]] (0x5C07): `OUT (C),A` to the VDP data port = write one byte
  to the auto-incrementing VRAM write address.
- [[dispatch_inline_table]] (0x5C2E): computed-jump dispatcher for the
  double-special commands (STOP / SET-SPECIAL / MULTI); the same generic
  trampoline the map-script and entity engines use.
