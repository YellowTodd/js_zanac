# zanac-re

Cleanroom reverse engineering of Zanac AI for MSX 1 (by Compile, 1986).

See `plan.md` (top level) for the full design. This README is the operator's quick reference.

## Quick start

```bash
# install the tool in editable mode
uv pip install -e tools/

# validate the knowledge base
zanackb validate

# emit symbol files for openMSX
zanackb symbols --format openmsx -o build/zanac.sym
zanackb symbols --format sjasm   -o build/zanac.sjasm.sym

# produce a fully commented source
zanackb annotate source/zanac.asm -o build/zanac-annotated.asm

# coverage report
zanackb coverage

# who references this address?
zanackb refs 0x4123
```

## Layout

- [source/zanac.asm](source/zanac.asm) — full game disassembly (use `sjasmplus`)

- [kb/data/](kb/data/) — structured binary regions (sprites, entities, tracks, data tables).
- [kb/guides/](kb/guides/) — cross-cutting subsystem notes.
- [kb/guides/conventions.md](kb/guides/conventions.md) — naming, confidence ladder, address syntax.
- [kb/guides/glossary.md](kb/guides/glossary.md) — MSX/Z80 vocabulary used across the KB.
- [kb/sprints/](kb/sprints/) — sprint briefs and their summaries (audit trail).
- [kb/subsystems/](kb/subsystems/) — detailed subsystem description.
- [kb/symbols/](kb/symbols/) — one Markdown file per labeled location.

- [savestates/](savestates/) — utility savestates for debugging.
- [scripts/](scripts/) — simple TCL and IPS cheats.
- [tools/](tools/) — Python package implementing the `zanackb` CLI and other tools.
- `build/` — generated artifacts; gitignored.

## Sprint loop

1. Pick or write the next `kb/sprints/NNNN-*.md` with `status: open`.
2. In Claude Code, issue the standing prompt (see `kb/sprints/README.md`).
3. Claude reads only the scoped source ranges + referenced KB entries.
4. Claude creates/updates entries under `kb/symbols/` and `kb/data/`.
5. Claude runs `zanackb validate` and fixes any errors.
6. Claude writes the sprint `## Summary` and flips `status: done`.
7. Operator reviews the diff, merges, and queues the next sprint.

## Dependencies

- Python 3.10+
- `pydantic>=2`, `pyyaml`, `python-frontmatter`, `click`
- openMSX with `-control stdio` support (optional, for verification sprints)
