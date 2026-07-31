---
id: "0004"
status: done
range: 0x43DA-0x445E
strategy: vector_table_walk
budget_turns: 30
---

# Sprint 0004 — VBLANK handler

## Goal
Decode the interrupt service routine patched into H_TIMI at cold_start (0x43DA),
identify its sub-calls, and document the frame counter, sprite-shadow, entity
dispatch loop, and the wait-one-vblank helper. Cross-reference against the known
`wait_frames` entry (0x5BEC) that already identifies 0xE1F8.

## Inputs
- `kb/symbols/0x4000-init/cold_start.md` — mentions H_TIMI patch, needs detail
- `kb/symbols/0x5000-gameplay/wait_frames.md` — names 0xE1F8 as frame counter
- `kb/symbols/0x4000-init/vdp_int_enable.md` — called inside entity loop
- `kb/symbols/0x4000-init/vdp_int_disable.md` — called from ISR
- `source/zanac.asm` lines 42–57 (cold_start: H_TIMI patch, RAM clear)
- `source/zanac.asm` lines 329–402 (entity-table init, sub_4306)
- `source/zanac.asm` lines 479–492 (check_start_key, ISR body at 0x43DA)
- `source/zanac.asm` lines 493–523 (entity_dispatch at 0x445F)
- `source/zanac.asm` lines 1257–1270 (sub_4e7b at 0x4E7B)

## Verification plan
- Static: confirm OUTI destination port (C) equals VDP data port from (0x0007).
- Dynamic: openMSX breakpoint at 0x43DA; watch 0xE1F8 tick once per frame.
- Dynamic: confirm entity table at 0xE300 populated during gameplay.

## Summary

Six new KB entries added; `cold_start` updated with H_TIMI patch detail.

**VBLANK ISR (0x43DA–0x445E, 133 bytes):**
Patched into H_TIMI by cold_start via `LD (0xFD9A), 0xC3; LD (0xFD9B), 0x43DA`.
Sequence: pop BIOS return addr off stack; call 0x013E (unknown BIOS call); disable
VDP interrupts; increment frame counter at 0xE1F8; fetch VDP data port from
BIOS ROM (0x0007); set VDP write address to SAT base (0x3B80); load sprite count
from 0xE11F; if non-zero, use OUTI loop to DMA sprite-shadow bytes from 0xE000 to
VDP; check entity-state flags; conditionally call 0x4560 (unknown); check player
entity slot at 0xE300; call 0x9A79 and 0x4E7B; restore register frame and RET.

**Entity dispatch (0x445F):**
Iterates 26 entity slots starting at 0xE300 (each 32 bytes, IX += 0x20); for each
non-zero slot byte calls a handler via jump table at 0x70B7; at loop end writes
walk-pointer low byte back to 0xE11F as the sprite count.

**wait_one_frame (0x4306):**
Enables VDP interrupt, loops polling 0xE1F8 until ≥ 1, zeros it, tail-calls
vdp_int_enable. Cleaner single-frame sync used outside the per-frame loop.

**Still uncertain:**
- Sub-call 0x013E at ISR start — sprint 0002 flagged as unknown.
- OUTI loop exact byte count per sprite slot (4 bytes / slot most likely).
- 0x9A79 — in enemy region; content not yet read.
- 0x4E7B — reads 0xE200 flag byte; bit 0 → fire trigger (JP 0x5182); exact role unclear.
- 0xE127 — toggle counter incremented in ISR every other frame; purpose unknown.

**Next sprint candidates:**
- **0005 — Entity-slot structure**: Decode one live entity slot at 0xE300+n during
  gameplay via openMSX; document the 32-byte struct (type, X, Y, pattern, HP, etc.).
- **0006 — Jump table at 0x70B7**: Read all entries, map entity-type IDs to handler
  addresses, identify player/bullet/enemy-type dispatch.
- **0007 — 0x9A79 (enemy update)**: Called every VBLANK; decode to find sprite
  coordinate update and collision logic.
