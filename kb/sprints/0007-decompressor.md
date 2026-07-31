---
id: "0007"
status: done
range: 0x5C3C-0x5D2B
strategy: forward_from_caller
budget_turns: 20
---

# Sprint 0007 — Decompressor

## Goal
Identify and document the graphics decompressor routine and its three loader
wrappers; map every compressed region to its exact VRAM destination. The
compression format is already known from `xtra/zanac-decoder.py` (`decode()`
function) and was used to produce `kb/features/graphics-data.md`.

## Inputs
- `xtra/zanac-decoder.py` — reference implementation of the algorithm
- `kb/data/gfx_*.md` — confirmed ROM ranges for each compressed region
- `source/zanac.asm` lines 1976–2043 (`sub_5c3c`, `sub_5c60`, `sub_5ca5`)
- `source/zanac.asm` lines 2044–2100 (`sub_5ccf`, `sub_5d1a`)
- `source/zanac.asm` lines 165–170 (main-loop call sites)
- `source/zanac.asm` lines 329–332 (`init_screen_mode` call site)
- `source/zanac.asm` lines 1591–1594 (second call site for `sub_5c3c`)

## Verification plan
- Static: cross-check VRAM destinations with sprint-0003-confirmed table
  addresses (PGT=0x0000, SGT=0x1800, CT=0x2000, NT=0x3800).
- Static: verify `sub_5ccf` stop-handler restores original DE (ROM addr),
  explaining why loaders use the same DE across 3 calls to 3 VRAM thirds.

## Summary

**`decompress_block` (0x5CCF) identified and decoded.** The Z80 routine is a
direct implementation of the Python `decode()` function in `xtra/zanac-decoder.py`:
- State: `D` = special escape byte (init 0xFF); `E` bit 0 = mode (0=copy, 1=repeat).
- Single special: toggle mode.
- Double special + 0x00: STOP — restores original DE/HL via saved stack frame.
- Double special + 0x01 + X: SET SPECIAL (handler at 0x5D02 within DB block).
- Double special + 0x02 + M + N: MULTI — inner loop processes N bytes M times
  from the same ROM position (handler at 0x5D06 within DB block).

**Key design: stop-handler restores original DE.** Because the STOP handler
(`POP HL; POP DE; POP BC; RET`) restores the initial DE (ROM source) and HL
(VRAM base), each loader calls `decompress_block` three times with the same DE
but HL += 0x800 to replicate data across all three Screen-2 PGT/CT sections.

**Three loader wrappers documented:**
- `load_logo_tiles` (0x5C3C): logo bitmap → PGT tiles 176+; logo colors → CT tiles 176+.
- `load_bg_tiles` (0x5C60): late-stage BG group-a at tile 23, group-b at tile 90.
- `load_charset_sprites` (0x5CA5): charset PGT 0–255 (×3); sprites SGT 0x1800; charset CT 0–255 (×3).

**VRAM layout cross-check (vs sprint-0003 confirmed values):**
- PGT = 0x0000 ✓ (charset tiles loaded there by `load_charset_sprites`)
- SGT = 0x1800 ✓ (sprite patterns loaded there by `load_charset_sprites`)
- CT = 0x2000 ✓ (charset colors loaded there)
- NT = 0x3800 (unchanged; not touched by loaders)

**`sub_5c2e` dual role confirmed:** Used both as entity-type dispatcher and as
the decompressor's command dispatcher (double-special commands 0/1/2).

**Still uncertain:**
- Call site for `load_bg_tiles` (0x5C60) not found in decoded code; likely
  triggered from a level-scroll or stage-boundary check in the main loop.
- The SET SPECIAL handler at 0x5D02 lives in a DB block; it uses a JP absolute
  to reach LAB_5cdd (cannot use JR — too far).

**Next sprint candidates:**
- **0008 — 0x9A79 (enemy update)**: Decode the routine called every VBLANK from
  the ISR; expect sprite coordinate update + collision detection.
- **0009 — Level scroll**: Find the routine that triggers `load_bg_tiles` and
  tracks horizontal scroll position / stage progression.
- **0010 — LAB_412A**: Decode the title-screen initializer at 0x412A that calls
  both `load_charset_sprites` and `load_logo_tiles`; understand the full boot flow.
