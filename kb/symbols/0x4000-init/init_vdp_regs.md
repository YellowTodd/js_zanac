---
address: 0x42BA
end: 0x42CE
kind: routine
name: init_vdp_regs
confidence: confirmed
calls:   [BIOS:RDVDP, BIOS:WRTVDP]
called_by: [0x428A]
sprint: "0040"
tags: [init, video, vdp]
---

# init_vdp_regs

## Summary

Writes VDP registers 0–7 from the inline `vdp_init_table` (0x42CF) to configure
Screen Mode 2 (Graphic II) for the game/title display. Called by
`init_screen_mode` (0x428A).

## Analysis (source 0x42BA–0x42CE)

```
42BA  CALL 0x013E        ; RDVDP — read VDP status (clears any pending int flag)
42BD  LD HL,0x42CF       ; HL → vdp_init_table
42C0  LD D,0x08          ; 8 registers
42C2  LD E,0x00          ; start at register 0
42C4  LD C,E             ; C = register number
42C5  LD B,(HL)          ; B = table value
42C6  CALL 0x0047        ; WRTVDP(reg C, value B)
42C9  INC HL; INC E; DEC D; JR NZ,0x42C4
42CE  RET
```

> **BIOS-label note:** the disassembler's `-> NAME` comments here are wrong.
> `0x013E` is **RDVDP** (not "sub_013e"), `0x0047` is **WRTVDP** (the disasm says
> DISSCR). Verified against `kb/symbols/0x0000-bios/`.

## Register values

See `vdp_init_table` (0x42CF) for the live-verified byte-by-byte decode. Summary:
name table 0x3800, colour table 0x2000, pattern table 0x0000, SAT 0x3B80, sprite
generator 0x1800, 16×16 sprites, display off at init (R1=0x82). Matches
`zanac-vdp-layout`.

## Confidence

`confirmed` — live trace (sprint 0040, `tools/trace_subsystem_a.py`): breaking at
the routine's RET (0x42CE) on a fresh boot, VDP registers R0–7 read back
`02 82 0E FF 03 77 03 01`, an exact match to `vdp_init_table`.
