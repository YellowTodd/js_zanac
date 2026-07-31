# Conventions

These rules are enforced by `zanackb validate` where possible and by reviewer discipline otherwise.

## Address syntax

- Always `0xNNNN`, lowercase `x`, uppercase hex digits.
- Never `NNNNh`, `$NNNN`, or decimal.
- Ranges use a single hyphen: `0x4100-0x4200`.
- The right endpoint is **inclusive** unless an entry has `end_exclusive: true`.

## Confidence ladder

| Level | Meaning | Evidence required |
|---|---|---|
| `confirmed` | Behavior verified by execution. | openMSX trace, memory diff, or visible in-game effect tied to the routine/data. |
| `likely`    | Strong static evidence. | Cross-references and call patterns consistent with the stated purpose; no contradicting evidence. |
| `hypothesis` | Plausible pattern, not yet checked. | A clear reason to suspect this is what it is (proximity, register usage, BIOS calls). |
| `guess`     | Placeholder name to avoid `loc_NNNN`. | None; just a hint so callers read better. Must be renamed or upgraded by a later sprint. |

Demotions (e.g. `confirmed` → `likely`) require a sprint note explaining why.

## Naming

- **Routines:** `snake_case`, verb-first. `update_sprite_shadow`, not `sprite_shadow_updater`.
- **Constants:** `SCREAMING_SNAKE_CASE`. `SPRITE_TABLE_BASE`.
- **Data regions:** `snake_case` with a type-ish suffix. `psg_track_0`, `level_1_map`.
- **BIOS thunks:** prefix `bios_`. `bios_wrtvrm`, `bios_chput`.
- **Unknown routines:** `sub_NNNN` (not `loc_NNNN`), so labels still hint at being callable code.
- **Unknown data:** `data_NNNN`.
- **Tags** (frontmatter `tags:`) are lowercase, hyphenated: `vblank`, `psg`, `sprite`, `slot-switch`.

## Frontmatter required fields

Every `kb/symbols/*.md` and `kb/data/*.md` must declare:

- `address` (int, parsed from `0xNNNN`)
- `kind` (`routine | data | constant | struct | port`)
- `name` (must match the conventions above)
- `confidence` (one of the four levels)
- `sprint` (the sprint id that last touched this entry)

Optional but recommended:

- `end` — last address covered (inclusive)
- `inputs`, `outputs`, `clobbers` — register conventions for `kind: routine`
- `calls`, `called_by` — cross-references (addresses or `BIOS:NAME`)
- `tags` — list

## File placement

- `kb/symbols/0xNNNN-area/<name>.md` — the leading `0xNNNN-area/` prefix groups related entries (e.g. `0x4000-init/`, `0x6800-video/`). The folder is a hint, not a contract.
- `kb/data/<name>.md` — flat; data entries are typically referenced by name.
- `kb/features/<subsystem>.md` — long-form prose tying multiple symbols into a story.

## Edits across sprints

- Sprint files are **append-only** once `status: done`. Corrections go in a new sprint that explains what changed and why.
- Symbol entries are mutable, but each edit must update `sprint:` to the sprint that made the change. The git history is the diff log.
