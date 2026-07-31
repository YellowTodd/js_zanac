---
id: "0003"
status: done
range: 0x4000-0x42FF
strategy: vector_table_walk
budget_turns: 30
---

# Sprint 0003 — VDP table layout

## Goal
Read VDP registers 0–7 live from openMSX after Zanac boots, derive the exact
VRAM addresses for name/pattern/colour/sprite tables, and confirm or correct
the values predicted by `init_vdp_regs` (0x42BA) and `kb/features/zanac-vdp-layout.md`.

## Inputs
- `kb/symbols/0x4000-init/init_vdp_regs.md` — predicted register values
- `kb/features/zanac-vdp-layout.md` — predicted VRAM map
- `kb/features/vdp-tms9918a.md` — register bit definitions
- `kb/symbols/0xF380-sysvars/rg0sav.md` … `rg7sav.md` — BIOS shadow addresses
- `source/zanac.asm` lines 406–420 (init_vdp_regs inline table at 0x42CF)

## Verification plan
- Launch openMSX with `connect_subprocess`, power on, let BIOS boot.
- Set BP at 0x42F8 (vdp_int_enable) so we catch the moment after VDP init.
- Read VDP registers 0–7 from BIOS shadow (RG0SAV–RG7SAV, 0xF3DF–0xF3E6).
- Derive VRAM table addresses and compare to `zanac-vdp-layout.md`.
- Read a sample of VRAM to confirm tile data at computed addresses.

## Summary

All eight VDP registers confirmed live via openMSX (BP at 0x42F8 after init).
Shadows at RG0SAV–RG7SAV (0xF3DF–0xF3E6) match the ROM inline table at 0x42CF
(`02 82 0E FF 03 77 03 01`) exactly. VRAM layout fully verified by direct reads:

| Table | Predicted | Confirmed |
|-------|-----------|-----------|
| Name table (PN) | 0x3800 | ✓ title-screen text visible |
| Color table (CT) | 0x2000 | ✓ color data present |
| Pattern table (PG) | 0x0000 | ✓ ASCII tile data present |
| Sprite attribute table (SAT) | 0x3B80 | ✓ sprite 0 Y=0xD0 terminates list |
| Sprite generator table (SGT) | 0x1800 | ✓ patterns 0–3 contain game sprites |

**New findings not in prior sprints:**

1. **BIOS shadow divergence**: `enable_display`/`disable_display` toggle VDP R1 BL bit
   without updating RG1SAV (0xF3E0). After first call: shadow=0x82, actual VDP=0xC2.

2. **Title-screen layout confirmed**: 7-digit score at VRAM 0x3809 (right-aligned),
   7-digit top score at 0x3815 (right-aligned), "SCORE"/"TOP" labels in cyan (color 7),
   score digits in light red (color 9).

3. **Score BCD = 7 digits**: `score_hi` holds 3 BCD digits (digits 5–7), making max
   score 9,999,999. Default top score `00 10 00` → "  10000".

4. **Publisher/developer confirmed**: credits say "GAME DESIGNED BY COMPILE",
   "PRODUCED BY AII", "PRESENTED BY PONY INC.", "COPYRIGHT @ 1986 PONY INC."

5. **Sprite pattern 1** (0x1820–0x183F): small oval/diamond — player bullet or shot.
   Patterns 2–3 also contain game sprite data.

**Still uncertain:** sprite colour registers (all sprites at colour 0 during title
screen). Player ship sprite pattern number unknown (needs gameplay sprint).

**Next sprint candidates:**

- **0004 — VBLANK handler**: The ISR at 0x43DA (patched into H_TIMI at cold_start)
  likely increments 0xE1F8 (frame counter), updates the SAT, and calls the sound
  engine. Decoding it roots the main game loop call graph.
- **0005 — Sprite attribute table update**: Find which routine fills the SAT at
  0x3B80 each frame and trace the player/enemy sprite coordinate logic.
- **0006 — Score rendering pipeline**: Trace the BCD score increment → render
  pipeline from the game event (enemy kill) through BCD add to `render_score_bcd`.
