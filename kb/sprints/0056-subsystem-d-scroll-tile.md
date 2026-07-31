---
id: "0056"
status: done
range: 0x94c3-0x97e2,0x9537-0x95a7,0x9678-0x97d4
strategy: subsystem_slice
subsystems: [D]
---

# Sprint 0056 — Subsystem D (Scroll & Tile Rendering): the map-script interpreter

## Goal

Close subsystem D (was ~65%). The core readers (`scroll_map_reader`,
`place_tile_group`, `load_stream_slots`, `init_stream_slot`) were `hypothesis`,
and two large "unmapped DB" blocks (0x9678–0x97D5, 349 B; 0x9537–0x95A8, 113 B)
plus the 0x93AB table were unexplained. Determine what drives the scroll engine
and resolve those blocks.

## Method

1. Static trace of the per-column reader `sub_94c3` (0x94C3): found it dispatches
   a **13-entry inline jump table at 0x94EB** via `sub_5c2e` — i.e. it is a
   row-triggered **map-script command interpreter**, and the "unmapped DB" blocks
   are its command handlers.
2. Disassembled the code-in-DB handlers with `redisasm patch` (0x9537–0x95A7,
   0x9678–0x97D4) and re-marked four embedded data tables with `redisasm data`
   (`map_cmd_jump_table`, `round_banner_text`, `glyph_col_data_973e`,
   `cmd11_index_table`). `redisasm verify` → ROM byte-identical.
3. Live confirmation (`tools/scroll_confirm.py`): non-breaking probes on the
   command dispatch, the program-counter state, and the per-frame routines.

## Summary

**Subsystem D → fully documented ✓.** The vertical-scroll engine is driven by a
**row-triggered map-script interpreter** ([[map_script_step]] 0x94C3): the level
data (0xA65C–0xB7A5) is a forward-only stream of commands, each prefixed by the
map row at which it fires. Full format + 13-command table: [[level_script_format]].

### Headline finding — it's a bytecode interpreter

`sub_94c3` advances `level_row_ctr` (0xE702) one map row per column. When the row
counter reaches `next_cmd_row` (0xE706) it fetches the next command byte at the
program counter `stream_ptr` (0xE704), masks the low nibble, and computed-jumps
through the inline table at 0x94EB. Otherwise it builds one tile column via
[[scroll_precompute]] → [[scroll_map_reader]]. Each handler ends `JP 0x97D5`,
which reads the next 2-byte row trigger and loops — so several commands may fire
on one row, and triggers are non-decreasing.

The 13 commands cover the whole subsystem and reach into others: load/modify
column-group & inner stream slots (cmds 2–7), ground-tile placement with
collision check (cmds 0/1 → `check_col_clear`), spawn-pace nudges (cmd C → I),
the **"ROUND n" intermission banner** (cmd 8), a VRAM glyph blit (cmd A), and the
**round-script jump** (cmd 9 → `sub_9433` → [[resolve_round_from_ptr]] →
`stage_stream_ptr_table`), which ties D to K (round flow) and E (level data).

### Confirmed (live, `tools/scroll_confirm.py`, round 1)

- **Program-counter model**: `stream_ptr` walked forward 0xA75B→0xA760→0xA76C→
  0xA77A as `next_cmd_row` stepped 30→50→80→110 and `level_row_ctr` climbed to
  each trigger — a command fires exactly when row == trigger.
- Commands **2, 5, 8** observed dispatched at 0x94E8.
- **cmd 8 = ROUND banner**: print site 0x96BF fired once at round start;
  0xE701 = round number 1.
- `scroll_vram_write` (0x9A79) ≈ 60 hits/s (per-VBLANK); `scroll_map_reader`
  (0x9888) runs continuously under the driver.

### Disassembled (redisasm, verified byte-identical)

- 0x9537–0x95A7 (113 B) → cmd handlers 3–5.
- 0x9678–0x97D4 (349 B) → cmd handlers 6–12 (incl. ROUND banner).
- Data re-marked: `map_cmd_jump_table` (0x94EB), `round_banner_text` (" ROUND ",
  0x96C2), `glyph_col_data_973e`, `cmd11_index_table` (0x976C).

### Corrections

- **`scroll_map_reader` 0xE702 is the scroll-row counter, not a stage index.**
  `0x9888` uses `(0xE702)&3` / `&7` only to pick a per-row tile-block *phase*;
  the round/stage number is 0xE701. Bumped to `likely` (live-confirmed running).
- **cmd 8 (0x9699) is the "ROUND n" banner**, not merely a wide-structure pointer
  set — it does both. **cmd A (0x96E5) is a VRAM glyph blit**, not entity spawn.
  Corrected in [[level_script_format]] (now `confirmed`).
- **0x93AB is NOT subsystem D.** It is a base-attack pattern table (8 LE word
  pointers + 4-byte descriptors) read by the base handler at 0x8FDE via rotating
  cursor 0xE717 → owned by **G**. CLAUDE.md/db-sections updated.

### New / updated KB

- New: [[map_script_step]] (0x94C3, the interpreter; covers converge point
  0x97D5, init `sub_940c`/`sub_9405`, round jump `sub_9433`).
- Updated: [[level_script_format]] (command table corrected, `confirmed`),
  [[scroll_map_reader]] (0xE702 fix), [[build_tile_screen]], [[scroll_state]]
  (0xE71C, 0xE720), `db-sections-with-code.md`, CLAUDE.md.

### Tools

`tools/scroll_confirm.py`.

### Remaining (minor, do not block "done")

- Per-round content of 0x9B64–0xBE27 (the script *data*) stays with subsystem E.
- Consumers of 0xE71C (cmd 6) and the exact byte-grammar of cmds 0/1/3/4/A
  operands not modelled to the byte.
