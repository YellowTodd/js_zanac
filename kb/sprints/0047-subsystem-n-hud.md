---
id: "0047"
status: done
range: 0x4996-0x49EF,0x4A74-0x4A99,0x4AA5-0x4ACD,0x4AEA-0x4B29,0x4B83-0x4BC6,0x4BD4-0x4C8A
strategy: subsystem_slice
budget_turns: 30
subsystems: [N]
---

# Sprint 0047 — Subsystem N (HUD & Status Display): confirm all render routines

## Goal

Take subsystem N to fully documented (all `confirmed`). Most render routines were
`hypothesis`/`likely`; the digit-pattern source, VRAM target rows, and the
unmapped 0x4AEA–0x4B83 DB block needed resolving.

## Inputs

- `kb/subsystems/N-hud-and-status-display.md`
- `kb/symbols/0x4900-hud/*` (score/round/level/lives render routines)
- Source: 0x4996–0x49EF (score render), 0x4A74 (add_score), 0x4AA5 (milestone),
  0x4AEA (award table), 0x4B83/0x4B8D (digit), 0x4BD4 (labels), 0x4C4D/0x4C68/0x4C74.

## Verification plan

`tools/sprint0047_verify.py` — micro-exec: plant values, hijack PC to each
routine, trap on a stack sentinel (or the 0x4A26 exit for add_score), read back
the VRAM/score the routine produced. Game left halted between calls.

## Summary (filled at end)

**All 19 checks passed; subsystem N → fully documented ✓.**

### Confirmed (render chain → VRAM, micro-exec)

| Routine | Evidence |
|---------|----------|
| `render_score_bcd` 0x49B5 | score `12 34 56` → "123456"; `00 00 42` → "    42" (leading-zero spaces) |
| `render_lives_score` 0x4996 | score→0x3809, topscore→0x3815 |
| `render_topscore_row2` 0x49A7 | topscore→0x38B8 |
| `render_score_row2` 0x49AF | score→0x3918 |
| `write_digit_to_vram` 0x4B83 | **2-digit** (A=42→"42", A=5→" 5"); 0x4B8D = 3-digit (137→"137") |
| `render_round_digit` 0x4C68 | E701=5 → " 5" at 0x3A1B |
| `update_status_bar` 0x4C4D | round/level/lives → 0x3A1B/0x39BB/0x397A |
| `render_hex_byte` 0x4C74 | 0xAB→"AB", 0x3C→"3C", 0x07→"07" |
| `add_score` 0x4A74 | idx 1/9/13 → +1/+100/+1000, = `score_award_table[idx]` |
| `draw_hud_labels` 0x4BD4 | wrote "SCORE " at 0x38F9 |

### Corrections

- **0x4C68 was mis-named `render_hiscore_digit`** — it renders the **round**
  (E701) at 0x3A1B. Renamed `render_round_digit`.
- **0x4DA5 ("update_fire_display") removed from N** — it is the STOP-key
  `pause_handler` (K/input, sprint 0032). The FIRE readout *value* is rendered by
  the fire-weapon handler (≈0x730B, F) using N's digit primitives.
- **0x4AEA block is the `score_award_table`** (3-byte BCD point values), not "HUD
  glyph data" — score digits use font tiles (0x30+digit). The adjacent
  `data_4b2a` (0x4B2A–0x4B82) is a separate unreferenced table (likely ALC).
- `write_digit_to_vram` (0x4B83) is **2-digit**; the 3-digit variant is 0x4B8D.

### New symbols / data

- New: `render_hex_byte` (0x4C74), `draw_hud_labels` (0x4BD4), `add_score`
  (0x4A74), `score_award_table` (0x4AEA, data); renamed `render_round_digit`.
- Source: 12 HUD `SUB_ram_*` labels renamed to their KB names; `score_award_table`
  + `data_4b2a` labels added. `redisasm verify` byte-identical.

### Files

- 7 symbol files `hypothesis`/`likely` → `confirmed`; 3 new symbols + 1 data;
  removed `render_hiscore_digit.md`.
- `N-hud-and-status-display.md` coverage `done`, gaps cleared; `CLAUDE.md` N → done ✓
  and DB tracker updated (0x4AEA resolved; 0x4B2A flagged for I).
- `tools/sprint0047_verify.py`.

`zanackb validate` 0 errors. `redisasm verify` byte-identical.
