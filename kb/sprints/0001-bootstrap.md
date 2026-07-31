---
id: "0001"
status: done
range: 0x4000-0x4010
strategy: bootstrap
budget_turns: 40
---

# Sprint 0001 — Bootstrap

## Goal
Stand up the tooling and the knowledge-base conventions. This sprint does
not analyze game logic; it establishes the round-trip:

```
kb/*.md  --zanackb-->  build/zanac.sym, build/zanac-annotated.asm
```

## Scope
- Define `kb/conventions.md` and `kb/glossary.md`.
- Implement `tools/zanackb/`:
  - `parser.py` (pydantic schema + frontmatter loader)
  - `validate.py` (overlaps, broken refs, duplicates)
  - `emit_symbols.py` (openmsx, sjasm)
  - `annotate.py` (line-based comment injection)
  - `openmsx.py` (TCL socket client)
  - `cli.py` (click CLI)
- Seed three KB entries to exercise the round-trip:
  - `bios_keyint` @ `0x0038`
  - `rom_header` @ `0x4000-0x400F`
  - `cold_start` @ `0x4010` (hypothesis)
- A toy `source/zanac.asm` containing the seeded addresses.

## Verification plan
- `zanackb validate` exits 0.
- `zanackb symbols --format openmsx` emits exactly 3 lines.
- `zanackb annotate source/zanac.asm` emits a banner before the
  `4010` line containing `cold_start`.

## Summary

Tooling and conventions in place. KB schema is `extra="forbid"`, so typos in
frontmatter field names fail loudly. Address overlaps, duplicate names, and
references to non-KB addresses are surfaced by `zanackb validate`.

The annotator does not parse Z80; it injects comments by matching addresses
on each line of the disassembler's output. Two patterns are recognized by
default (line-leading `NNNN:` and trailing `; 0xNNNN`); the user can extend
`ADDRESS_PATTERNS` in `annotate.py` to match other disassembler styles.

The openMSX client speaks the length-free `<command>...</command>` framing
over a unix socket; it supports `read_memory`, `write_memory`,
`set_breakpoint`, `step`, `cont`, `reset`. Verification sprints can use it
from a TCL action body (set a breakpoint that calls back into a logging
script) or by polling memory after each frame.

## Next sprint candidates

- **0002 — BIOS-call survey.** Scan `source/zanac.asm` for every `call`/`jp`
  whose target lies in `0x0000-0x3FFF`. Each one tells us something about
  surrounding code; produce a draft KB entry for every distinct caller.
- **0003 — Vector-table walk.** Find the VBLANK hook patches (`HKEYI`,
  `HTIMI`) and the routines they install. These root the call graph.
