---
id: "0068"
status: done
range: 0x4000-0xBFFF
strategy: tooling
budget_turns: 30
subsystems: [all]
---

# Sprint 0068 — Naming-consistency pass (KB ↔ zanac.asm)

> **Completion-plan final sprint.** Run **last** — names only firm up once all
> content sprints (0062–0067) have landed. Three mechanical passes: inventory,
> decide-in-KB, apply-byte-neutrally.

## Motivation

The disassembly still carries generic `SUB_ram_XXXX`/`LAB_ram_XXXX` labels at
entry points whose purpose the KB has long since named, plus a handful of
**legacy misnomers** where the label contradicts the documented behaviour —
canonical example: `reset_enemies_and_psg` (0x516C) is a pure **stop-all-sound**
(clears 5 voice slots' active flags, falls through to `mute_psg_channels`;
"enemies" is legacy, flagged in the docs). A reader of `zanac.asm` should see
the KB's understanding in the labels themselves.

**Scope guard:** only routine/data **entry-point** labels are renamed.
`LAB_ram_*` targets reached solely by JR/DJNZ/conditional jumps from within the
same routine (loop and branch labels) stay generic.

## Goal

### Pass 1 — inventory (`tools/naming_audit.py`)

Join KB `name:` fields (symbols + data entries) against the labels present in
`source/zanac.asm`. Emit:

- **(a) unlabeled:** KB-named symbols whose asm label is still generic
  (`SUB_ram_`/`LAB_ram_` at a documented entry point) or missing entirely;
- **(b) misnomers:** label ≠ KB name, or names the KB flags as wrong — seed the
  list by grepping kb/ for `misnomer`, `legacy`, `wrong`, correction
  blockquotes;
- **(c) local labels** (JR/DJNZ-only targets) — listed but excluded from
  renaming.

### Pass 2 — decide in KB first

For every (b) item: rename in the KB entry (file name + `name:` field), keeping
the old name on an `aka:`/alias line so older sprint docs still resolve; update
`[[wikilinks]]` across kb/. The KB is the source of truth for pass 3. Known
candidates to adjudicate: `reset_enemies_and_psg` → `stop_all_sound`;
`handler_type72_base_core` → orb naming (0059 correction); sweep for others.

### Pass 3 — apply byte-neutrally (`tools/rename_symbol.py`)

Because `zanac.asm` uses absolute hex operands with `; -> NAME` comments, a
rename never touches emitted bytes: it rewrites the label line plus every
`-> NAME` comment. Build `tools/rename_symbol.py <old> <new>`:

- refuses if `<new>` already exists or `<old>` is ambiguous;
- renames the `old:` label line and all `-> old` comment references;
- preserves column alignment (tabs = 8, per session rules).

For symbols with no label yet, use the existing
`tools/redisasm.py add-label --addr 0xNNNN` then rename. Batch the work
(one subsystem area per batch), running the gate after each batch.

## Inputs

- `kb/symbols/**`, `kb/data/*` frontmatter (`name:`, `address`)
- `tools/redisasm.py` (add-label, verify) + `kb/guides/redisasm-protocol.md`
- Memory note: the `-> NAME` comments on **BIOS** calls are systematically
  wrong (Ghidra legacy) — BIOS thunk names come from `kb/symbols/0x0000-bios/`,
  and BIOS-range fixes belong in this sprint's pass 3 too if cheap.

## Verification plan

- **Gate after every batch:** `tools/redisasm.py verify` (ROM identity — the
  assembled bytes must not change) + `zanackb validate`.
- Final: `tools/naming_audit.py` reports zero (a)/(b) items; spot-read 5
  random routines to confirm labels + `->` comments are coherent.
- `git diff` review shows only label lines and comments changed (user commits).

## Expected KB entries

- `tools/naming_audit.py`, `tools/rename_symbol.py`.
- Renamed KB entries with `aka:` aliases; wikilink updates.
- A short `kb/guides/naming-conventions.md` appendix (or a section in
  `conventions.md`): how names are chosen, the alias rule, the local-label
  exclusion.

## Summary (filled at end)

**Done 2026-07-06.** The disassembly's labels now mirror the KB's names, and the
change is provably byte-neutral (`redisasm.py verify` → ROM byte-identical after
every batch).

### Tools
- **`tools/naming_audit.py`** — Pass-1 inventory / gate. Joins KB `name:` fields
  vs asm labels → (a) unlabeled / (b) misnomer / (c) local-excluded, plus a
  residual-generic-arrow count. Exits non-zero until clean. **Final run: 0 (a),
  0 (b), 0 residual arrows.**
- **`tools/rename_symbol.py`** — Pass-3 applicator, address-keyed & KB-driven.
  `--from-kb` renames generic labels, inserts missing ones, **splits `DB` lines**
  for mid-block data entries, and retargets all three reference forms (def,
  symbolic `JR`/`DJNZ` operand, `; -> name` arrow) — re-aligning the col-64
  comment when an operand's width changes. Also a `<old> <new>` single form.

### Applied (all gated by `verify`, ROM byte-identical)
- **82 generic labels renamed**, **62 missing labels inserted**, **6 `DB`-lines
  split** (`logo_tile_rows` 0x4827, `entity_jump_table` 0x70B9 — stale 0x70B7
  label removed, `proto_box_sat_table` 0x7808, `edge_swooper_b_anim` 0x7E70,
  `level_script_format` 0xA65C, `tile_column_data_region2` 0xB7A6), **518+
  arrow/operand references** rewritten to KB names.
- **`base_segment_table`** (0x8DF1–0x8E13) reconverted from mis-decoded code to a
  labelled `DB` block via `redisasm data`, which resynced the absorbed
  **`handler_type80_base_damage`** entry at 0x8E14 (then labelled).
- **1 BIOS arrow** fixed (`0x0053 → SETWRT`, `fix_bios_comments.py`).

### Pass-2 KB adjudications
- **`reset_enemies_and_psg` → `stop_all_sound`** (0x516C) — the one true
  name-level misnomer; KB file renamed, `aka` note added, wikilinks updated
  across 11 kb/ files (append-only sprint docs resolve via the alias).
- `data_4b2a`→`structure_award_index_table`, `sub_4e7b`→`psg_sound_tick`,
  `glyph_col_data_973e`→`glyph_col_data`, `ROM_ID`→`rom_header`,
  `collision_check`(asm)→`collision_routine`(KB): stale/pre-KB labels aligned to
  the correct KB names.
- **`handler_type72_base_core` — kept** (systematic name correct; 0059 was a
  behaviour correction, noted in the entry).

### Notes
- **Byte-neutrality caveat found & handled:** relative `JR`/`DJNZ` use *symbolic*
  operands, so a def rename must update the operand too — the initial def-only
  pass broke assembly (22 "label not found" errors); `retarget()` fixes all three
  reference forms.
- New guide: `kb/guides/naming-conventions.md` (source-of-truth rule, alias rule,
  local-label scope guard, the three reference forms). `redisasm` KB_LABELS is a
  stale legacy dict and was intentionally not used as a name source.
- `zanackb validate`: 0 errors (79 pre-existing cross-ref warnings, unrelated).
