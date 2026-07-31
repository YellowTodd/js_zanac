---
id: "0002"
status: done
range: 0x4000-0xBFFF
strategy: bios_call_survey
budget_turns: 40
---

# Sprint 0002 — BIOS-call survey

## Goal
Scan `source/zanac.asm` for every `call`/`jp` whose target lies in `0x0000-0x3FFF`.
Each one tells us something about the surrounding code; produce a draft KB entry
for every distinct caller routine.

## Inputs
- `kb/symbols/0x0000-bios/` — existing BIOS entries (all `likely`)
- `source/zanac.asm` lines 205–240, 315–500, 670–790, 925–1000, 1080–1260,
  1340–1380, 1860–1970, 2845–2910, 3118–3400, 4288–4315, 5060–5089

## Findings

### Distinct BIOS targets (13 unique addresses, 39 callsites)

| Address | Label (disasm) | Count | Notes |
|---------|---------------|-------|-------|
| 0x0024  | ENASLT        | 1 JP  | map_page2 tail-call to enable slot |
| 0x0047  | "DISSCR"      | 5+1JP | **Likely WRTVDP** in this C-BIOS (see below) |
| 0x004D  | WRTVDP        | 1     | init_screen_mode |
| 0x0050  | RDVRM         | 1     | VRAM→RAM copy loop |
| 0x0053  | WRTVRM        | 11    | everywhere — tile/score writes |
| 0x0056  | SETRD         | 2     | VDP read-address setup |
| 0x0059  | SETWRT        | 2     | VDP write-address setup |
| 0x005C  | FILVRM        | 4     | region clears |
| 0x0093  | GICINI        | 2+1JP | PSG init / mute |
| 0x0096  | WRTPSG        | 2     | PSG register write (reg 14) |
| 0x0138  | (ext BIOS)    | 1     | slot register read in detect_slot |
| 0x013E  | (ext BIOS)    | 1     | called before VDP reg init |
| 0x0141  | (ext BIOS)    | 6     | keyboard matrix row read (SNSMAT) |

### Key discovery: 0x0047 is WRTVDP, not DISSCR

The disassembler labeled 0x0047 as "DISSCR" based on the standard MSX BIOS
jump table. However, every call site uses the WRTVDP calling convention
(B=data, C=register):

- `init_vdp_regs` (0x42BA): loops 8×, sets C=0..7, B from table → writes VDP
  registers 0-7. Values `02 82 0E FF 03 77 03 01` are Screen Mode 2 settings.
- `vdp_int_disable` / `vdp_int_enable` (0x42ED / 0x42F8): read VDP R1 shadow,
  modify one bit, pass B=shadow, C=1 to 0x0047.
- `disable_display` / `enable_display` (0x42D7 / 0x42E2): same pattern,
  modify bit 6 (BL).
- `explode_enemies` (0x8A26): calls with BC=0xF07 and 0x107.

In C-BIOS 1.1 the jump-table entry at 0x0047 is WRTVDP. The existing KB entry
`bios_disscr` at 0x0047 is incorrect for this ROM build; updated in this sprint.

### VDP register 1 shadow at 0xF3E0

The routines `disable_display`, `enable_display`, `vdp_int_disable`, and
`vdp_int_enable` all read a 16-bit word from (0xF3DF) and use the HIGH byte
(= byte at 0xF3E0) as the VDP register 1 mirror. This is read-modify-written
before calling WRTVDP. Our KB entry `vdpsts` at 0xF3E0 appears to actually be
the VDP register 1 shadow (RG1SAV) in this BIOS. Flagged for follow-up.

### Fast VDP write pattern

`vdp_write_byte_di` (0x5BFC) and `sub_5c07` (0x5C07) read the VDP data port
number from BIOS ROM at address 0x0007 (`LD BC, (0x0007)`) and use it as the
OUT port. This is a Zanac-specific fast-write routine that bypasses the BIOS
WRTVRM for sequential VRAM writes.

### VRAM address layout (inferred from VRAM addresses)

| VRAM range      | Purpose              |
|-----------------|----------------------|
| 0x3800–0x397F   | Name table (Screen 2 third) |
| 0x3809, 0x3815  | Lives score display  |
| 0x38B8, 0x3918  | Top-score rows       |
| 0x3839, 0x3859  | HUD score display    |
| 0x396A          | Weapon indicator (5 tiles) |
| 0x397A          | Level display        |
| 0x39BB          | Level number tile    |
| 0x3A1B          | Hi-score digit       |
| 0x3ABD          | HUD numeric display  |
| 0x3C00–0x3E3F   | (alternate name table or buffer) |

## New KB files created

### Extended BIOS
- `kb/symbols/0x0000-bios/sub_0138.md`
- `kb/symbols/0x0000-bios/sub_013e.md`
- `kb/symbols/0x0000-bios/bios_snsmat.md` (0x0141)

### Initialization cluster (0x4200–0x4400)
- `kb/symbols/0x4000-init/disable_display.md` (0x42D7)
- `kb/symbols/0x4000-init/enable_display.md` (0x42E2)
- `kb/symbols/0x4000-init/vdp_int_disable.md` (0x42ED)
- `kb/symbols/0x4000-init/vdp_int_enable.md` (0x42F8)
- `kb/symbols/0x4000-init/init_vdp_regs.md` (0x42BA)
- `kb/symbols/0x4000-init/init_screen_mode.md` (0x428A)
- `kb/symbols/0x4000-init/read_options.md` (0x4343)
- `kb/symbols/0x4000-init/check_start_key.md` (0x43D2)

### Slot mapping (0x4E00)
- `kb/symbols/0x4000-init/map_page2.md` (0x4E45)
- `kb/symbols/0x4000-init/detect_slot.md` (0x4E50)

### HUD / score display (0x4900–0x4E00)
- `kb/symbols/0x4900-hud/render_score_bcd.md` (0x49B5)
- `kb/symbols/0x4900-hud/render_lives_score.md` (0x4996)
- `kb/symbols/0x4900-hud/render_topscore_row2.md` (0x49A7)
- `kb/symbols/0x4900-hud/render_score_row2.md` (0x49AF)
- `kb/symbols/0x4900-hud/write_digit_to_vram.md` (0x4B83)
- `kb/symbols/0x4900-hud/update_status_bar.md` (0x4C4D)
- `kb/symbols/0x4900-hud/render_hiscore_digit.md` (0x4C68)
- `kb/symbols/0x4900-hud/update_fire_display.md` (0x4DA5)

### Low-level gameplay helpers (0x5000–0x5FFF)
- `kb/symbols/0x5000-gameplay/reset_enemies_and_psg.md` (0x516C)
- `kb/symbols/0x5000-gameplay/tile_to_vram_addr.md` (0x5BDD)
- `kb/symbols/0x5000-gameplay/vdp_write_byte_di.md` (0x5BFC)
- `kb/symbols/0x5000-gameplay/wait_frames.md` (0x5BEC)
- `kb/symbols/0x5000-gameplay/vdp_set_addr_write.md` (0x5C25)

### Enemy (0x8000)
- `kb/symbols/0x8000-enemy/explode_enemies.md` (0x8A26)

## Updated KB files
- `kb/symbols/0x0000-bios/bios_disscr.md` — demoted to `hypothesis`, added
  note that 0x0047 is WRTVDP in this C-BIOS version.

## What is still uncertain

1. **0x0138, 0x013E** — true purpose unknown without reading C-BIOS ROM bytes.
   0x0138 is very likely a slot-register read; 0x013E might be a DISSCR thunk.
2. **VDP shadow at 0xF3E0** — labeled `vdpsts` in KB but code uses it as
   VDP R1 mirror. Needs verification with openMSX memory read.
3. **0x0047 vs DISSCR** — confirmed by pattern but not yet verified via
   openMSX breakpoint on the BIOS jump table.
4. **VRAM layout** — the full name/color/pattern table layout is partially
   inferred. A VDP-registers sprint would lock this in.

## Summary

39 BIOS callsites resolve to 13 distinct BIOS targets. The dominant pattern is
the WRTVRM/SETRD/SETWRT/FILVRM quartet used throughout the display pipeline,
and GICINI/WRTPSG for audio. A cluster of four tiny routines (42D7/42E2/42ED/
42F8) manages VDP register 1 bits (display enable + interrupt enable) by
reading a shadow at 0xF3E0. A major labeling error was found: 0x0047 is WRTVDP
in this C-BIOS version, not DISSCR. 0x0141 is the keyboard matrix scanner
(SNSMAT equivalent), called with A=row 4–8 to read joystick/fire buttons.

## Next sprint candidates

- **0003 — VDP table layout.** Read VDP registers 0-7 via openMSX after boot,
  map the name/pattern/color table addresses, and cross-reference with the VRAM
  addresses already catalogued here.
- **0004 — VBLANK handler.** 0xFD9A is patched at cold_start to 0x43DA. Decode
  the ISR: it likely increments 0xE1F8 (frame counter), updates the SAT, and
  calls the sound engine. This roots the call graph into the main loop.
- **0005 — Score display.** Follow the BCD rendering pipeline from game-state
  RAM (0xE103-0xE108) through render_score_bcd to the VRAM name table.
