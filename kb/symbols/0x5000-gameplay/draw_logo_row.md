---
address: 0x5BA0
end: 0x5BDC
kind: routine
name: draw_logo_row
confidence: confirmed
inputs:
  HL: "target name-table coord (L=row, H=col) — the swirl position"
  A: "logo row index (selects the tile strip)"
outputs: {}
clobbers: [AF]
calls: [0x5BDD, 0x42ED, BIOS:SETWRT, 0x5BFC]
called_by: [0x5A68, 0x5A99]
tags: [title-screen, logo, name-table, vram]
sprint: "0042"
---

# draw_logo_row

## Summary

Blits one horizontal strip of the title logo into the name table at the given
swirl coordinate. The tile strip comes from `logo_tile_rows` (0x4827 + 25×row);
up to 18 tiles are written, **clipped at the right screen edge**. Off-screen
positions (row ≥ 0x18 or col ≥ 0x20) are skipped.

> Corrects the old `title_intro_seq.md` note that called this a "PSG-channel
> tick / sound engine" routine — it is the logo-row tile blitter, no audio.

## Analysis (source 0x5BA0–0x5BDC)

```
5BA0  PUSH BC/DE/HL/AF
5BA4  LD B,0x12          ; default 18 tiles
5BA6  LD A,L; CP 0x18; JR NC,5BD8   ; row off bottom → skip
5BAB  LD A,H; CP 0x20; JR NC,5BD8   ; col off right → skip
5BB0  CP 0x0E; JR C,5BB8            ; col < 14 → full width
5BB4  CPL; ADD A,0x21; LD B,A       ; col ≥ 14 → clip count = 0x20 − col
5BB8  CALL 0x5BDD        ; tile_to_vram_addr(HL) → VRAM name-table addr
5BBB  CALL 0x42ED        ; vdp_int_disable
5BBE  CALL 0x0053        ; SETWRT (VRAM write address)
5BC1  POP AF; PUSH AF; LD C,A
      ; A = 25*C (logo row index → tile-strip offset)
5BC3  ADD A,A;ADD A,A;ADD A,A;ADD A,C;ADD A,A;ADD A,C
5BCA  LD E,A; LD D,0; LD HL,0x4827; ADD HL,DE   ; HL → logo_tile_rows[row]
5BD1  LD A,(HL); CALL 0x5BFC; INC HL; DJNZ 5BD1 ; write B tiles
5BD8  POP AF/HL/DE/BC; RET
```

## Notes

- `0x5BFC` = `vdp_write_byte_di` (one tile → VRAM, ISR-safe).
- `0x5BDD` = `tile_to_vram_addr` (row in L, col in H → 0x3800 + row*32 + col).
- Tile data: `logo_tile_rows` (0x4827), stride 25 (`0x19`).

## See also

`logo_tile_rows` (0x4827), `lookup_swirl_coord` (0x5B91), `title_intro_seq`.
