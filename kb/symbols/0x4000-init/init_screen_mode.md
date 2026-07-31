---
address: 0x428A
end: 0x42B9
kind: routine
name: init_screen_mode
confidence: confirmed
calls:   [0x42BA, 0x5CA5, BIOS:FILVRM, BIOS:WRTVRM]
called_by: [0x4045]
sprint: "0040"
tags: [init, video]
---

# init_screen_mode

## Summary

One-time display setup run at the top of each title/game entry (called from the
`LAB_4042` loop at 0x4045): program the VDP registers, load the charset/sprite
patterns into VRAM, blank the name table, hide all sprites, and clear the entity
table. Leaves the screen ready but still display-off (enabled later by
`enable_display`).

## Analysis (source 0x428A–0x42B9)

```
428A  CALL 0x42BA        ; init_vdp_regs — write VDP R0–R7
428D  CALL 0x5CA5        ; load_charset_sprites — patterns → VRAM
4290  LD HL,0x3800; LD BC,0x300; LD A,0x20
4298  CALL 0x0056        ; FILVRM(0x3800, 0x300, 0x20) — fill name table with space (0x20)
429B  LD HL,0x3B80; LD A,0xD0
42A0  CALL 0x004D        ; WRTVRM(0x3B80, 0xD0) — SAT[0].Y = 0xD0 → sprite-list terminator (hide all sprites)
42A3  SUB A
42A4  LD (0xE11F),A      ; sprite_count = 0
42A7  LD (0xE120),A      ; 0xE120 = 0
42AA  LD B,0x20; LD HL,0xE300
            ; clear 0x20*0x20 = 0x400 bytes at 0xE300 (the entity table / SAT shadow region)
42B9  RET
```

> **BIOS-label note:** the disassembler mislabels these calls. `0x0056` is
> **FILVRM** (disasm says SETRD) and `0x004D` is **WRTVRM** (disasm says WRTVDP).
> Verified against `kb/symbols/0x0000-bios/`. So the two writes *clear the name
> table to spaces* and *hide sprites*, not "set a read pointer / write a VDP reg"
> as an earlier note claimed.

## Notes

- The 0xD0 written to SAT Y[0] is the TMS9918A end-of-sprite-list marker (Y=208),
  the standard way to suppress all sprites until the game repopulates the SAT
  shadow.
- The 0x400-byte clear at 0xE300 wipes the whole entity slot pool (32 slots ×
  32 bytes), see [[C-entity-framework]].

## Confidence

`confirmed` — live trace (sprint 0040, `tools/trace_subsystem_a.py`): at the RET
(0x42B9) on a fresh boot, VRAM 0x3800–0x3AFF read back all `0x20`, SAT[0].Y at
0x3B80 = `0xD0`, `0xE11F`/`0xE120` = 0, and 0xE300–0xE6FF (the entity pool) all
zero — every documented effect verified.
