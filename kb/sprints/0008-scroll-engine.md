---
id: "0008"
status: done
range: 0x986E-0x9AE3
strategy: forward_from_caller
budget_turns: 30
---

# Sprint 0008 — Scroll engine

## Goal
Decode the routine at 0x9A79 called every VBLANK from the ISR (previously
labelled "enemy update" — corrected here). Understand the full background-scroll
pipeline: how the level map is converted to tile rows, how those rows are
double-buffered, and how the ISR applies them to the name table.

## Inputs
- `kb/symbols/0x4000-init/vblank_isr.md` — ISR calls 0x9A79; label was wrong
- `source/zanac.asm` lines 3975–3996 (`sub_986e` — tile row extractor)
- `source/zanac.asm` lines 3997–4037 (`sub_9888` — level tile setup)
- `source/zanac.asm` lines 4038–4268 (`LAB_98d4` … `LAB_99fd` — map stream loop)
- `source/zanac.asm` lines 4269–4285 (0x9A79 DB block — VRAM writer)
- `source/zanac.asm` lines 4286–4298 (`sub_9ae4` — main-loop sync / wait-vblank)

## Verification plan
- Static: bit 0 of (0xE700) as DMA-ready handshake between main loop and ISR.
- Dynamic: openMSX breakpoint at 0x9A79; read (0xE714), (0xE715) each VBLANK;
  confirm name table VRAM 0x3800 changes by one new row per frame during scroll.

## Summary

**Correction:** 0x9A79 is NOT an "enemy update" — it is the background vertical-
scroll name-table writer, called by `vblank_isr` every frame. `vblank_isr.md`
updated accordingly.

**`scroll_vram_write` (0x9A79–0x9AC4):**
VBLANK ISR callback. Gated by bit 0 of (0xE700) (DMA-ready flag). Splits the 24
name-table rows at `scroll_row` (0xE714) and writes two buffer segments to VRAM:
- Rows [scroll_row..23]: from the buffer at (0xE715)
- Rows [0..scroll_row−1]: from 0xE800 (wrap-around segment)
Each row: WRTVRM to set address, then DI/OUT-loop/EI over 24 tile bytes. An
inner split-row path (IY+0 ≠ 0) handles columns that straddle the circular-buffer
boundary using a secondary OUT loop with a different byte count.

**`scroll_sync` (0x9AE4):**
Main-loop VBLANK sync. Enables VDP interrupt, spins while bit 0 of (0xE700) is
set, then initialises scroll_row = 0 and tile_buf_ptr = 0xE800 for the new frame.
This is what main-loop callers (lines 177, 322, 3179, 3405) use to wait for the
name-table update to complete before preparing the next frame's scroll data.

**`scroll_map_reader` (0x9888):**
Main-loop routine (hypothesis). Reads level map ROM data from a set of 8 stream
slots at 0xE2E0 (each 4 bytes), assembles a 24-byte tile row in 0xEA48 via a
tile-ID lookup table at 0xEA40, then LDIR-copies it to the buffer at (0xE715)
for the ISR to write. Level-specific tile tables at 0xA444/0xA4A4/0xA564 (ROM)
are selected by stage index from (0xE702).

**DMA handshake confirmed:**
```
main loop precomputes row → SET (0xE700) bit 0 → call scroll_sync (spin)
VBLANK ISR → scroll_vram_write clears bit 0, writes VRAM → sync exits
```

**New KB files:** `scroll_vram_write`, `scroll_sync`, `scroll_map_reader`,
`scroll_state` (0xE700–0xE71A). Updated: `vblank_isr` (corrected 0x9A79 label).

**Still uncertain:**
- 0xE704–0xE713: fields between scroll_flags and scroll_row not decoded.
- 0xE2C0–0xE2DF: the 4-entry "column-group" outer stream table.
- How bit 0 of (0xE700) is SET — which routine triggers the scroll DMA each frame.
- Exact format of the level tile tables at 0xA444 (ROM).

**Next sprint candidates:**
- **0009 — Collision detection**: Find the routines at 0x95A8 and 0x95ED called
  from `scroll_map_reader`; determine whether they check player/bullet/tile
  collision or are purely tile-management helpers.
- **0010 — Level map format**: Read the tile tables at 0xA444–0xA563 to understand
  the level map encoding and stage progression.
- **0011 — openMSX live survey**: Set a breakpoint at 0x9A79 during gameplay,
  read (0xE714)/(0xE715)/(0xE700), and confirm the scroll-state field layout.
