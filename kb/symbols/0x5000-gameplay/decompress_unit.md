---
address: 0x5D1A
end: 0x5D2B
kind: routine
name: decompress_unit
confidence: confirmed
inputs:
  A: literal byte to emit
  E: bit0 = mode (0 = copy one, 1 = repeat)
  HL: ROM source pointer (used only in repeat mode, to read the count)
outputs:
  HL: advanced past the count byte in repeat mode
clobbers: [B]
calls: [0x5C07]
called_by: [0x5CE2, 0x5D0F]
tags: [decompress, rle, vram]
sprint: "0037"
---

# decompress_unit

Emits one copy/repeat *unit* of the RLE stream consumed by [[decompress_block]].
The byte to emit is already in `A`; the current mode is `E` bit 0.

```
5D1A  PUSH BC
5D1B  BIT  0,E            ; mode: 0 = copy, 1 = repeat
5D1D  JR   NZ,5D23        ; repeat -> read explicit count
5D1F  LD   B,1            ; copy -> emit once
5D21  JR   5D25
5D23  LD   B,(HL)         ; repeat -> count byte from stream
5D24  INC  HL
5D25  CALL vdp_write_byte ; (0x5C07) write A
5D28  DJNZ 5D25           ; ... B times
5D2A  POP  BC
5D2B  RET
```

- **Copy mode** (`E` bit0 = 0): write `A` exactly once.
- **Repeat mode** (`E` bit0 = 1): read the next stream byte as a count `B`,
  advance `HL`, and write `A` that many times.

The single-byte-at-a-time output goes through [[vdp_write_byte]] (0x5C07), which
streams to the auto-incrementing VDP write address. Called from the main
decompress loop (0x5CE2) for normal literals and from the MULTI handler (0x5D0F)
inside the "repeat N bytes M times" expansion.
