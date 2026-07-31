---
address: 0xE11F
kind: data
name: sprite_count
confidence: likely
sprint: "0004"
tags: [sprite, vblank]
---

# sprite_count

## Summary
1-byte count of active sprite slots written to the SAT shadow (0xE000) this frame.
Written by `entity_dispatch` (0x445F) after processing all entity slots; read by
`vblank_isr` to size the OUTI DMA transfer into the VDP SAT.

## Analysis
Source lines 340 (`LD (0xE11F), A` — zeroed at init alongside 0xE120), 495
(`LD (0xE122), HL` — walk pointer saved), 521–522 (`LD A, (0xE122); LD (0xE11F), A`
— walk pointer low byte written as sprite count after dispatch loop), 485 (`LD A,
(0xE11F)` — read by ISR before DMA).

The value is the low byte of the sprite-shadow walk pointer (base 0xE000), which
equals the number of bytes written, i.e. sprite_count × bytes_per_sprite_entry.
