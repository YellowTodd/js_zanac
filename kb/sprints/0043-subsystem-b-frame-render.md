---
id: "0043"
status: done
range: 0x42D7-0x42FF,0x4306-0x4318,0x43F8-0x4448,0x48A9-0x48CF,0x5BDD-0x5C04
strategy: subsystem_slice
budget_turns: 24
subsystems: [B]
---

# Sprint 0043 — Subsystem B (Frame / Render Pipeline): confirm all routines

## Goal

Take subsystem B to fully documented (all `confirmed`). Five routines were
already `confirmed`; nine were `likely` and the VBLANK SAT-DMA path was
described inside `vblank_isr` but not split into its own entry. Execution-verify
the nine and split out the DMA segment.

## Inputs

- `kb/subsystems/B-frame-render-pipeline.md`
- `kb/symbols/0x4000-init/{vblank_isr,disable_display,enable_display,vdp_int_disable,vdp_int_enable,wait_one_frame,sprite_shadow_push,sprite_sat_write}.md`
- `kb/symbols/0x5000-gameplay/{wait_frames,tile_to_vram_addr,vdp_write_byte_di,vdp_set_addr_write}.md`
- Source: ISR DMA block 0x43F8–0x4448; the small VDP/timing routines above.

## Verification plan

`tools/sprint0043_verify.py` — openMSX, in-game state. Two techniques:

1. **Micro-exec harness** (pure / near-pure routines): pause CPU, set input regs,
   point SP at a scratch stack holding a sentinel return address (0xE7F0), set PC
   to the routine, breakpoint the sentinel, run, read outputs. Used for
   `tile_to_vram_addr`, `vdp_write_byte_di`, `vdp_int_disable/enable`,
   `disable/enable_display`, `sprite_sat_write`, `wait_one_frame`, `wait_frames`.
2. **Live observation** (game must stay healthy → run *before* any micro-exec,
   which leaves PC/SP hijacked): hit-count breakpoint on `sprite_shadow_push`
   (0x48A9), memory diff of SAT shadow 0xE000 vs VRAM 0x3B80, frame-counter
   write-watchpoint on 0xE1F8.

## Summary (filled at end)

**All 19 checks passed; subsystem B → fully documented ✓.**

### Confirmed (likely → confirmed)

| Addr | Routine | Evidence |
|------|---------|----------|
| 0x5BDD | `tile_to_vram_addr` | unit tests: `(col,row)→0x3800+row*32+col` for 4 inputs |
| 0x5BFC | `vdp_write_byte_di` | SETWRT then write; byte landed in VRAM (3 addrs) |
| 0x42ED/0x42F8 | `vdp_int_disable`/`vdp_int_enable` | R1 shadow (0xF3E0) bit 5 cleared→set (0xC2→0xE2) |
| 0x42D7/0x42E2 | `disable_display`/`enable_display` | R1 shadow bit 6 cleared→set (0xA2→0xE2) |
| 0x48B8 | `sprite_sat_write` | fake slot → shadow `[53 50 38 0F]` (Y−0x11), 0xE122 +4 |
| 0x4306 | `wait_one_frame` | trap-returns, zeroes 0xE1F8 |
| 0x5BEC | `wait_frames` | B=20 blocked 0.30 s (≈0.34 s @59 Hz) |
| 0x48A9 | `sprite_shadow_push` | 85 hits/0.5 s via entity_update fall-through |

### New entry — SAT-DMA split out (gap closed)

`sat_dma_to_vram` (0x43F8–0x4448), `confirmed`. Inline ISR segment that DMAs the
SAT shadow at 0xE000 → VRAM 0x3B80 via `OUTI` blocks (normal path + 5S flicker
path using counter 0xE127), then writes the Y=0xD0 terminator. Live: shadow vs
VRAM = **126/128** bytes (2-byte moving-sprite read race, matches sprint 0018).
Source label `sat_dma_to_vram:` added at 0x43F8; `redisasm verify` byte-identical.
Cross-linked from `vblank_isr` step 7.

### Files

- 9 symbol files `likely`→`confirmed` with live-confirmation notes, `sprint: 0043`.
- New `kb/symbols/0x4000-init/sat_dma_to_vram.md`.
- `vblank_isr.md` step 7 points to the split-out entry.
- `B-frame-render-pipeline.md`: coverage `done`, gaps closed, DMA entry added.
- `tools/sprint0043_verify.py`.

`zanackb validate` 0 errors. `redisasm verify` byte-identical.
