---
address: 0x9AA6
end: 0x9AE3
kind: routine
name: scroll_vram_inner
confidence: likely
inputs:
  A: "row count to write"
  DE: "RAM source tile-row buffer (0xE715 ptr, or 0xE800 for wrapped rows)"
  HL: "VRAM name-table write address (0x3800 base)"
  BC: "VDP data port number in C (from word at 0x0007)"
  IY: "0xE180 per-row status array"
outputs: {}
clobbers: [AF, BC, DE, HL, IY]
calls: ["BIOS:SETWRT"]
called_by: [0x9A9B]
tags: [scroll, vram, vblank, name-table]
sprint: "0033"
---

# scroll_vram_inner

## Summary
Inner VRAM write loop of [[scroll_vram_write]] (0x9A79). Streams `A` rows of
24 tile bytes each from a RAM buffer (`DE`) into the Screen-2 name table via
the VDP data port, handling per-row column-split (wrap-around) rows. This is
the routine that actually performs the scroll DMA each VBLANK.

## Analysis
Source lines 7907–7948. Entered with `B = A` (row count); `scroll_vram_write`
calls it twice — once for the rows below the split (`DE = (0xE715)`) and once
for the wrapped rows at the top (`DE = 0xE800`).

```
LD B, A                  ; outer = row count
LAB_9AA7:
  CALL 0x0053            ; SETWRT — set VDP write address to HL (row start)
  PUSH BC
  LD A, (IY+0) ; AND A
  JR NZ, LAB_9AC5        ; non-zero -> split row
  ; --- simple row: 24 sequential bytes ---
  LD B, 0x18
  DI ; LD A,(DE) ; OUT (C),A ; EI ; INC DE ; DJNZ
  LD BC, 0x0020 ; ADD HL, BC   ; HL += 32 (next name-table row)
  INC IY                       ; next per-row status entry
  POP BC ; DJNZ LAB_9AA7
  RET
LAB_9AC5:                ; --- split row: two segments ---
  LD B, A               ; first segment length = (IY+0)
  PUSH HL ; PUSH BC ; PUSH DE
  DI ; LD A,(DE) ; OUT (C),A ; EI ; INC DE ; DJNZ   ; emit first segment
  LD C, (IY+0x18) ; ADD HL, BC      ; advance VDP addr by split offset
  CALL 0x0053                       ; SETWRT for the wrapped half
  POP DE ; EX DE,HL ; ADD HL,BC ; EX DE,HL
  LD A, 0x18 ; SUB C ; POP BC ; LD B, A   ; second length = 24 - split
  POP HL
  JR LAB_9AB3           ; emit second segment, then continue outer loop
```

Each VDP byte write is bracketed by `DI/EI` because the VDP address
auto-increments and a mistimed interrupt (the sound/scroll ISR also touches the
VDP) would corrupt the write sequence.

## Per-row status array (0xE180, IY) — a protection window, not a wrap split
(corrected 2026-07-30)

This entry previously read the nonzero path as a "column-split (wrap-around)"
row. It is a **protected-window** mechanism: the second segment advances the
VDP address *and the source pointer by the same C* (`POP DE / EX / ADD HL,BC`
at 0x9AD8), so columns `[B, C)` of the row are simply **never repainted** —
the blit writes `[0,B)` and `[C,0x18)` and leaves the hole alone. Scroll
wrap-around is handled elsewhere, by the ring and `scroll_vram_write`'s
two-call structure.

| Field | Meaning |
|-------|---------|
| `(IY+0) = B` | columns written before the window (0 = no window) |
| `(IY+0x18) = C` | window **end** column; protected width = `C − B` |

The consumer is the "ROUND n" banner: map cmd 8 prints at VRAM 0x3948 (row 10)
and the window keeps the text on screen while terrain scrolls beneath;
`clear_title_state` (0x41CB) zeroes 0xE180–0xE1AF — exactly the two 24-entry
tables (B's and C's) — when `display_timer_countdown` (0x41BA) runs 0xE15E
down, letting the next blit reclaim the area. (Which routine writes the
window values for the banner is not yet pinned; the mechanism and its teardown
are.)

## Cross-references
- Outer driver and the scroll-split setup: [[scroll_vram_write]].
- VBLANK handshake bit (0xE700 bit 0) and buffer pointers: [[scroll_state]].
- `0x0053` = SETWRT (set VRAM write address); see `bios_setwrt`.
