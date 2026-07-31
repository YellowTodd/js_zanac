---
address: 0x5C07
end: 0x5C0F
kind: routine
name: vdp_write_byte
confidence: confirmed
inputs:
  A: byte to write to VRAM at the current auto-incrementing VDP write address
outputs: {}
clobbers: []
calls: []
called_by: [0x5C19, 0x5D25]
tags: [vram, vdp, decompress]
sprint: "0037"
---

# vdp_write_byte

The lowest-level VRAM output primitive of the decompressor / VRAM-print family.

```
5C07  PUSH BC
5C08  LD   BC,(0x0007)   ; sysvar 0x0007 = VDP data-port number in C
5C0C  OUT  (C),A         ; write A to the VDP data port
5C0E  POP  BC
5C0F  RET
```

Writes one byte (`A`) to the VDP data port. The VDP write address must already
be set (via BIOS `SETWRT` 0x0053 or an earlier write) and auto-increments after
each `OUT`, so repeated calls stream bytes into consecutive VRAM cells.

`(0x0007)` is the ROM-mapped sysvar holding the VDP data-port I/O address; using
`LD BC,(0x0007); OUT (C),A` is the standard MSX pattern for a port read from a
variable.

Callers: [[decompress_unit]] (0x5D25 inner write loop) and the string-copy loop
[[vram_string_copy]] (0x5C19).
