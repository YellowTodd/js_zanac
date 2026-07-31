# Zanac Reverse-Engineering Documentation Plan

A design for LLM-assisted documentation of the Zanac (MSX 1) disassembly, driven by short automated sprints, a human-editable Markdown knowledge base, and tooling that round-trips to an openMSX-verifiable symbol table and a fully annotated source.

## Repository layout

```
zanac-re/
  source/              # raw disassembly — read-only
    zanac.asm
  kb/
    symbols/           # one .md per labeled location (or per cluster)
      0x4000-init/cold_start.md
      0x6800-video/update_sprites.md
    data/              # binary data with structure
      sprite-format.md
      psg-track-0.md
    features/          # cross-cutting subsystems
      sound-engine.md
      scrolling.md
    sprints/
      0001-bios-call-survey.md
      0002-vblank-handler.md
    conventions.md
    glossary.md
  tools/
    zanackb/           # Python package
      __init__.py
      parser.py
      emit_symbols.py
      annotate.py
      validate.py
      openmsx.py
      cli.py
  build/               # generated, gitignored or separate branch
    zanac.sym
    zanac-annotated.asm
    coverage.md
```

The original disassembly never gets edited. Everything Claude produces lives under `kb/` or `tools/`; everything machine-generated lives under `build/`.

## Knowledge base entry format

Markdown with YAML frontmatter — readable in any editor, trivially parseable, and friendly to git diffs.

```markdown
---
address: 0x4123
end: 0x4156          # optional, for sized regions
kind: routine        # routine | data | constant | struct | port
name: update_sprite_shadow
confidence: likely   # confirmed | likely | hypothesis | guess
inputs:  { HL: "shadow table base", B: "sprite count" }
outputs: { AF: clobbered }
calls:   [0x40A0, "BIOS:WRTVRM"]
called_by: [0x4500, 0x4612]
tags: [video, sprite, vblank]
sprint: 0002
---

# update_sprite_shadow

## Summary
Copies the 32-entry sprite attribute shadow at 0xE100 to VRAM 0x1B00.

## Analysis
Loops B times, reading 4 bytes per sprite...

## Verification
- Breakpoint at 0x4123 fires once per VBLANK (openMSX trace).
- After call, VRAM[0x1B00..0x1B7F] equals RAM[0xE100..0xE17F].
```

A few conventions to lock in early in `conventions.md`:

- **Confidence ladder.** `confirmed` = verified by execution/emulator; `likely` = strong static evidence (cross-refs match, ROM behavior consistent); `hypothesis` = plausible pattern, not yet checked; `guess` = placeholder so it isn't `loc_4123` forever.
- **Naming.** `snake_case` for routines, `SCREAMING` for constants, `bios_*` mirror for thunks, prefix unknowns with `sub_` (not `loc_`) so labels still mean something.
- **Address syntax.** Always `0xNNNN`, never `NNNNh` or `$NNNN`, so regex is trivial.

## Sprint protocol

A sprint is one `sprints/NNNN-slug.md` file. Claude Code reads it as the brief, works the scope, and updates it with a summary at the end. Strict scope keeps context small.

```markdown
---
id: 0002
status: open        # open | done | abandoned
range: 0x4100-0x4200
strategy: forward_from_caller   # or: data_table | callgraph_leaf | pattern
budget_turns: 30
---

## Goal
Identify the routine called from the VBLANK hook at 0x4040.

## Inputs
- kb/symbols/0x4040-vblank.md (confirmed)
- source/zanac.asm lines 8320–8480

## Verification plan
- Set BP at 0x4123 in openMSX, confirm hits every frame.
- Diff RAM 0xE100 vs VRAM 0x1B00 after one frame.

## Summary (filled at end)
...
```

Selection strategies that work well in practice, in roughly the order I'd run them:

1. **BIOS-call survey** — every `call NNNN` to a known BIOS entry tells you something about the surrounding code (text out, VDP, keyboard, slot).
2. **Vector-table walk** — VBLANK hook, RST vectors, interrupt mode 1 handler. These root your call graph.
3. **Callgraph leaves first** — small leaf routines are the easiest wins and turn into named tools for understanding callers.
4. **Data-table sweeps** — find `ld hl, NNNN` followed by table reads; classify the table once and dozens of callers become legible.
5. **Pattern matching** — once you've named one PSG track player, the others usually share structure.

## Python tool (`zanackb`)

CLI roughly:

```
zanackb validate                      # frontmatter schema, address overlaps, broken refs
zanackb symbols --format openmsx -o build/zanac.sym
zanackb symbols --format sjasm   -o build/zanac.sjasm.sym
zanackb annotate source/zanac.asm -o build/zanac-annotated.asm
zanackb coverage                      # % addresses labeled, by confidence
zanackb refs 0x4123                   # who calls/is called by this
```

Internals worth getting right early:

- **One parser, schema-validated.** Use `python-frontmatter` + a `pydantic` model for the YAML. Reject unknown fields loudly — typos in `condifence` are the enemy.
- **Address index.** Build a single `dict[int, SymbolEntry]` in memory; everything else (annotate, refs, symbols) is a view over it.
- **Annotate by line, not by parse.** Read the raw `.asm`, regex out the address column, look up in the index, prepend a `; — name (confidence) —` block plus inline trailing comments. Don't try to re-parse Z80 — let the disassembler's output be the spine.
- **Data regions get a separate renderer.** A `kind: data` entry with a `format:` field (e.g. `psg_track`, `sprite_pattern_8x16`) can pretty-print the bytes as a table or as ASCII art into the annotated output. Worth having a small plugin registry so you can add new formats per sprint.
- **OpenMSX symbol file.** The native format is `label: equ 0xNNNN` lines; openMSX also reads sjasm/pasmo `.sym`. Emit both.

## OpenMSX hookup

openMSX exposes a TCL command socket (`openmsx -control stdio` or the unix socket under `~/.openMSX/sockets/`). A small `tools/zanackb/openmsx.py` wrapper around `socket` + length-prefixed XML is enough for:

- `set_bp 0xNNNN { puts "hit" }` — drop a breakpoint from a sprint script.
- `debug read memory 0xNNNN N` — dump RAM/VRAM snapshots for verification.
- `debug step` / `cont` — drive single-stepping.
- `debug set_watchpoint write_io 0xA0` — catch PSG register writes for the sound-engine sprint.

Have the tool write verification transcripts back into the sprint's `## Verification` section as fenced code blocks. That way the evidence lives next to the claim.

## Driving from Claude Code

In Claude Code, your top-level instruction becomes a short, repeatable prompt — something like:

> Open `kb/sprints/NNNN-*.md` with status `open`. Read only the source ranges and KB entries it references. Stay inside the turn budget. Update or create entries under `kb/symbols/` and `kb/data/`, run `zanackb validate`, then write the `## Summary` and flip status to `done`. Report back: what was added, what's still uncertain, what the next sprint should be.

Two practical guardrails:

- **Context discipline.** Always have Claude Code load source with bounded `view` ranges driven by the sprint frontmatter, never the whole file. Cross-references resolve through `zanackb refs` calls, not by re-reading source.
- **Append-only sprints.** Old sprint files stay as the audit trail. When a `hypothesis` later becomes `confirmed`, that's a one-line edit in the symbol's frontmatter plus a note in the new sprint — not a rewrite of history.

If you want, the next step I'd suggest is sketching the `pydantic` schema and the `validate`/`annotate` CLI as the very first sprint's deliverable — that way every subsequent sprint already has a working round-trip from KB to annotated source.
