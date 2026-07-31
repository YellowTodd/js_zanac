# Naming conventions & the KB ↔ disassembly label bridge

How symbol names are chosen, how the disassembly's labels are kept in sync with
the KB, and which labels are deliberately left generic. Established by sprint
0068 (the naming-consistency pass); the base spelling rules live in
[conventions.md](conventions.md) §Naming.

## The KB is the source of truth

Every routine/data **entry point** in `source/zanac.asm` that the KB has named
carries that exact name as its label. The KB `name:` field is authoritative;
the disassembly follows it. Two tools maintain the bridge:

- **`tools/naming_audit.py`** — inventory / gate. Joins KB `name:` fields against
  the asm labels and classifies every documented address:
  - **(a) unlabeled** — KB-named entry whose asm label is still generic
    (`SUB_ram_XXXX` / `LAB_ram_XXXX`) or missing;
  - **(b) misnomer** — asm carries a *named* label that differs from the KB
    name, or the KB body flags its own name as a legacy misnomer;
  - **(c) local** — generic labels with no KB entry (see below), listed but
    excluded from renaming.
  It exits non-zero while any (a)/(b) item is open, so it doubles as the
  completion gate. **A clean run reports 0 (a)/(b) items and 0 residual generic
  arrow comments.**

- **`tools/rename_symbol.py`** — byte-neutral applicator.
  - `--from-kb` aligns every asm label in `[start,end]` (default the
    0x4000–0xBFFF ROM) to its KB name: it renames a generic/mismatched label,
    inserts one where an entry has none, or **splits a `DB` line** when the entry
    starts mid-block, and rewrites every inbound reference. Idempotent — re-runs
    are no-ops once clean.
  - `<old> <new>` renames a single label.

## Why renaming is byte-neutral

`zanac.asm` addresses every `CALL`/`JP` with an **absolute hex operand**
(`CALL 0x516c`), so those labels are cosmetic — renaming a definition or an
`; -> NAME` arrow comment never changes an emitted byte. The **exception** is
relative `JR`/`DJNZ`, which the disassembler emits with a *symbolic* operand
(`JR NZ, LAB_ram_412a`); renaming such a target must update the operand too (the
tool does, re-aligning the tab-positioned comment at visual column 64). Every
change is gated by `tools/redisasm.py verify` (assembles → byte-compares ROM).

A label token can appear three ways on a line — as the `name:` definition, as a
symbolic `JR`/`DJNZ` operand, and in a `; -> name` arrow comment. `rename_symbol`
retargets all three by address.

## The alias rule

When a KB entry is renamed because its old name was **wrong** (not merely
generic), the retired name is kept as an **`aka`** note in the entry body — never
a frontmatter field (the schema forbids extras). This lets append-only sprint
docs that still say the old name resolve to the current entry. Example:
[[stop_all_sound]] carries `aka reset_enemies_and_psg` (the pre-0068 misnomer;
it only ever touched the PSG, never enemy state).

## Local labels stay generic (the scope guard)

Only routine/data **entry-point** labels are named. `LAB_ram_XXXX` targets
reached solely by `JR`/`DJNZ`/conditional jumps **within the same routine**
(loop tops and branch joins) keep their generic form. Operationally the rule is
simple: **an address is renamed iff the KB documents an entry there.** Local
branch targets are never in the KB, so they are excluded automatically —
`naming_audit.py` lists them under (c). As of 0068 there are ~240 such local
labels, referenced by ~860 `JR`/`DJNZ` arrows.

## Names the KB flagged, and the 0068 adjudications

- `reset_enemies_and_psg` → **`stop_all_sound`** (0x516C): the sole genuine
  name-level misnomer; renamed, old name kept as `aka`.
- `data_4b2a` → `structure_award_index_table`, `sub_4e7b` → `psg_sound_tick`,
  `glyph_col_data_973e` → `glyph_col_data`, `ROM_ID` → `rom_header`: pre-KB
  Ghidra labels aligned to their (correct) KB names.
- `collision_check` (asm) → **`collision_routine`** (KB name kept): the KB entry
  deliberately packages both hitbox helpers under `collision_routine`; the asm
  label was aligned down to it.
- `handler_type72_base_core` — **kept.** The systematic `handler_typeNN_` scheme
  is intact and the type-72 designation is correct; the 0059 "orb/warp"
  correction was a *behaviour* clarification (documented in the body), not a
  name error. See [[handler_type72_base_core]].

BIOS-thunk arrow comments (Ghidra used a misaligned BIOS symbol table) are
corrected separately by `tools/fix_bios_comments.py`.
