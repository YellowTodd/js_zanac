---
address: 0x43F8
end: 0x4448
kind: routine
name: sat_dma_to_vram
confidence: confirmed
inputs:
  A': VDP status S#0 (captured at ISR top; bit 6 = 5S "too many sprites")
  B: SAT byte count (= 0xE11F, active_sprites × 4)
  BC-port: (0x0007) = VDP data port 0x98
outputs:
  VRAM: SAT at 0x3B80 written from shadow at 0xE000
clobbers: [AF, BC, DE, HL]
calls: []
called_by: [0x43DA]
tags: [sprite, vblank, sat, dma, isr]
sprint: "0043"
---

# sat_dma_to_vram

## Summary

Inline **SAT-shadow → VRAM DMA** segment of `vblank_isr` (0x43F8–0x4448). Copies
the sprite-attribute-table shadow at **0xE000** into VRAM **0x3B80** via tight
`OUTI` blocks, then writes the SAT terminator (Y=0xD0). It is not a `CALL`ed
subroutine — it is reached by fall-through inside the ISR after the SAT write
address has been set (`SETWRT 0x3B80`) and the byte count loaded from 0xE11F.
Split out of `vblank_isr` as its own entry (gap closed, sprint 0043).

## Two paths

The ISR restores the VDP status byte S#0 into `A` (`EX AF,AF'` at 0x43F8) and
tests **bit 6 = 5S** ("fifth sprite" / too many sprites on a line):

- **Normal path (5S clear, 0x4405–0x4410):** `LD HL,0xE000` then
  `OUTI / LD A,(0x0000) / LD A,(DE) / JR NZ` — streams all `B` shadow bytes
  straight to VRAM, with two dummy reads per byte as VDP write-timing padding.
- **Flicker path (5S set, 0x43FD–0x443E):** increments the flicker counter at
  **0xE127**; on odd counts it offsets the DMA source within 0xE000 by ±8 bytes
  (`+4`, then `−8` via `LD DE,0xFFF8`), rotating which 4-sprite subset is drawn
  first to spread the hardware per-line sprite limit across frames. The inner
  loop emits 4 bytes per iteration (`OUTI ×4` at 0x4424/0x442C/0x4434/0x443C).

Both paths converge at **0x4440**: `LD A,0xD0 / OUT (C),A` writes the SAT
terminator Y-byte (208) so the VDP stops scanning sprites past the active count.

## State

- **0xE000** — SAT shadow base (4 bytes/sprite: Y, X, name, colour/EC).
- **0xE11F** — byte count to DMA (= active_sprites × 4); 0 ⇒ segment skipped.
- **0xE122** — shadow walk pointer, reset to 0xE000 each frame by `entity_dispatch`.
- **0xE127** — 5S flicker counter (incremented only on the flicker path).
- VRAM **0x3B80** — hardware SAT in Screen 2.

## Live confirmation (sprint 0043)

Memory diff during active gameplay: **126/128 bytes** of shadow 0xE000 matched
VRAM 0x3B80 (the 2 mismatches are a read race on a sprite that moved between the
RAM and VRAM samples) — reproduces the sprint 0018 result. `tools/sprint0043_verify.py`.

## See also

- `vblank_isr.md` — 0x43DA, the ISR this segment lives inside.
- `sprite_sat_write.md` — 0x48B8, fills the 0xE000 shadow this DMAs.
- `sprite_shadow_push.md` — 0x48A9, motion+anim before the SAT append.
