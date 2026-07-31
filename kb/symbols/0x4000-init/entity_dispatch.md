---
address: 0x445F
kind: routine
name: entity_dispatch
confidence: confirmed
clobbers: [AF, BC, DE, HL, IX]
calls:   [0x42F8]
called_by: [0x40F2, 0x939F]
tags: [entity, sprite, dispatch]
sprint: "0044"
---

# entity_dispatch

## Summary
Iterates all 26 active entity slots, calls each slot's type-specific handler via
a ROM jump table, then writes the resulting sprite count back to 0xE11F.

## Analysis
Source lines 493–523.

```
LD HL, 0xE000
LD (0xE122), HL     ; save sprite-shadow walk pointer
LD B, 0x1A          ; 26 iterations (0x1A)
LD IX, 0xE300       ; first entity slot
loop:
  CALL 0x42F8       ; vdp_int_enable — re-enable VDP IRQ between slots
  PUSH BC
  LD A, (IX+0)      ; slot[0] = entity type byte
  OR A
  JP Z, next        ; type 0 = inactive, skip
  ADD A, A          ; type * 2 (word index)
  LD HL, A (zero-extended)
  ADD HL, DE=0x70B7 ; ROM jump table at 0x70B7
  LD HL, (HL)       ; fetch handler address
  LD BC, next       ; set return address
  PUSH BC
  JP HL             ; call handler (returns to next via PUSH/JP idiom)
next:
  ADD IX, 0x20      ; advance to next 32-byte slot
  POP BC
  DJNZ loop
LD A, (0xE122)      ; walk pointer low byte = bytes written to shadow
LD (0xE11F), A      ; → sprite_count
RET
```

Entity slots: 26 × 32 bytes = 832 bytes at 0xE300–0xE51F.
Jump table at 0x70B7 maps entity-type IDs (× 2) to handler routine addresses.
`vdp_int_enable` is called each iteration to allow VBLANK to fire during the
potentially long entity update phase.

## Index arithmetic — bit 7 is dropped

The dispatcher does `ADD A,A` on the **full** type byte (not `AND 0x7F` first),
then `LD L,A / LD H,0`. Active entities carry bit 7 set (e.g. player = 0x81), so
`ADD A,A` shifts bit 7 out of the 8-bit accumulator: the effective index is
`(type*2) & 0xFF`, which equals `(type & 0x7F) * 2`. Handler =
`*(0x70B7 + (type & 0x7F)*2)`. This is why `entity_jump_table` is documented with
virtual base 0x70B7 and indexed by the masked type.

## Live confirmation (sprint 0044)

- Executes ~32×/0.5 s during gameplay (one call per frame).
- A capture breakpoint at the `JP HL` site (0x4486) recorded the resolved handler
  for each dispatched slot: `t1→0x75D5` (player), `t44→0x82D0`, `t61→0x8302`,
  `t39→0x8525` — every one matches `*(0x70B7 + (type&0x7F)*2)` in ROM.
- At loop end (0x448F) `0xE122` low byte = `0xE11F` afterward (0x18 = 6 sprites ×4),
  confirming the sprite byte-count write-back. `tools/sprint0044_verify.py`.
