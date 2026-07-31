---
id: "0040"
status: done
range: 0x4010-0x4041,0x428A-0x42CE,0x4343-0x43BF,0x4E45-0x4E7A
strategy: subsystem_slice
budget_turns: 20
subsystems: [A]
---

# Sprint 0040 — Subsystem A (Boot & Hardware Init) documentation slice

## Goal

First subsystem slice: resolve the `hypothesis`-level gaps in [[A-boot-and-init]]
(`init_screen_mode`, `init_vdp_regs`, `detect_slot`, `read_options`) and correct
anything stale, working from the source against the correct MSX BIOS semantics.

## Inputs

- `kb/subsystems/A-boot-and-init.md`
- `kb/symbols/0x4000-init/{cold_start,init_screen_mode,init_vdp_regs,detect_slot,map_page2}.md`
- `kb/symbols/0x4000-init/read_options.md` (→ rewritten as `read_player_input.md`)
- `kb/data/vdp_init_table.md`, `kb/symbols/0x0000-bios/` (correct BIOS addresses)
- Source: 0x4010–0x4041 (cold_start), 0x428A–0x42CE, 0x4343–0x43BF, 0x4E45–0x4E7A

## Summary (filled at end)

**Key discovery — the disassembler's BIOS `-> NAME` comments are systematically
wrong.** Decoding the boot routines against the KB's own `0x0000-bios/` addresses
flipped several conclusions:

- `0x013E` = **RDVDP**, `0x0047` = **WRTVDP**, `0x004D` = **WRTVRM**, `0x0056` =
  **FILVRM**, `0x0093` = **WRTPSG**, `0x0096` = **RDPSG**, `0x0138` = **RSLREG**,
  `0x0141` = **SNSMAT**. The disasm labels these as DISSCR/GICINI/etc.

### Routines upgraded `hypothesis` → `likely`

- **`init_vdp_regs`** (0x42BA): RDVDP then WRTVDP×8 from `vdp_init_table`.
- **`init_screen_mode`** (0x428A): init_vdp_regs + load_charset_sprites, then
  **FILVRM(0x3800,0x300,0x20)** (blank name table to spaces) and
  **WRTVRM(0x3B80,0xD0)** (SAT Y[0]=0xD0 → hide all sprites), zero sprite_count,
  clear the 0x400-byte entity table at 0xE300. (Old note had both BIOS calls wrong.)
- **`detect_slot`** (0x4E50): RSLREG + EXPTBL(0xFCC1) slot search; returns the
  cartridge's full slot ID.
- **`map_page2`** (0x4E45): mirrors the running cartridge slot into page 2 via
  ENASLT (clarified wording).

### Major correction — `read_options` was misidentified

`0x4343` is **not** a boot/title option reader. It is the per-frame
**player-input poll**, called from the player-ship handler (0x7612) and from
`fire_edge_detect` (0x46BC) — never from boot. It reads both joystick ports (PSG
R14/R15) and keyboard rows 8/6/5 (SNSMAT), merges them active-low into the input
byte **0xE100**, and derives the horizontal-velocity selector into **0xE10C**
(`player_x_vel`; 4 = centre, then indexed into the X-velocity table at 0x7758).

- Renamed `read_options` → **`read_player_input`** (file + source label + both
  call-site comments); reassigned from subsystem A to [[F-player-ship-and-weapons]].
- The old "GICINI/mute PSG" and "difficulty → E10C" claims were both wrong.
- This removes the only ALC lead in [[I-alc-adaptive-difficulty]] (it was a false
  lead) — ALC remains genuinely unmapped.

### Other fixes

- `cold_start`: 0xE107=0x10 is the `topscore_mid` seed (default hi-score 100000),
  not "scroll speed"; 0xE701=1 is the stage/round index.
- DB block **0x4317–0x4343** is embedded code (16-bit math helper) and
  **0x43C0–0x43D1** is the **PRNG** (writes `prng_state` 0xE12B) — corrected the
  DB-region tracker (was guessed as "option data").

### Verification

`redisasm.py verify` → **ROM byte-identical** after the source label rename.
`zanackb validate` → 0 errors. A coverage ~70% → ~85%.

---

## Follow-up (same session) — A marked fully documented ✓

1. **Fixed all wrong BIOS comments** in `zanac.asm` via `tools/fix_bios_comments.py`
   (maps operand → correct name from `kb/symbols/0x0000-bios/`). 50 arrows rewritten
   (WRTVDP/WRTVRM/SETRD/SETWRT/FILVRM/LDIRMV/LDIRVM/WRTPSG/RDPSG/RSLREG/RDVDP/SNSMAT).
   ROM byte-identical. Checkpoint saved as `zanac-05.asm`.

2. **Live trace** (`tools/trace_subsystem_a.py`) promoted four routines to
   `confirmed`:
   - `init_vdp_regs` — VDP R0-7 read back `02 82 0E FF 03 77 03 01` (= `vdp_init_table`).
   - `init_screen_mode` — name table all 0x20, SAT[0].Y=0xD0, sprite_count=0,
     entity table 0xE300–0xE6FF all zero.
   - `detect_slot` — on the (non-expanded) test machine it exits early via `RET P`
     at 0x4E67; resolved slot captured at `map_page2`'s 0x4E4A: **A=0x01**, E=0x02.
   - `map_page2` — ENASLT maps slot 1 at page 2; page-2 ROM readable afterward.

3. **Disassembled the embedded code** (redisasm patch, ROM byte-identical):
   - `mul_a_e` (0x4317) — 8×8→16 unsigned multiply.
   - `div_hl_e` (0x4329) — 16÷8 round-to-nearest divide; called by 0x4CDB.
   - `prng_next` (0x43C0) — advances `prng_state`; called by spawn code
     (0x71C5/0x83A5/0x8686). Labels added; caller comments updated.

**Subsystem A → fully documented.** All A-owned routines are `confirmed`, no
`hypothesis` entries and no unmapped DB regions remain in A's range. Boundary
routines (`load_bg_level`, sound/title/frame calls from `cold_start`) are owned
and documented by their own subsystems. A coverage → **done ✓**.
