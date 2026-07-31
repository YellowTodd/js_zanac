# Sprints

A sprint is one scoped batch of analysis, recorded as `NNNN-slug.md` in this
folder. Each file is both the brief (read at the start) and the audit trail
(its `## Summary` section is filled in at the end).

## Standing prompt for Claude Code

Paste this prompt at the start of a sprint session:

> Open `kb/sprints/NNNN-*.md` with `status: open`. Read **only** the source
> ranges and KB entries it references — do not load `source/zanac.asm` in
> bulk. Stay inside the sprint's `budget_turns`.
>
> For each routine or data region you identify:
>   1. Create or update an entry under `kb/symbols/` or `kb/data/`.
>   2. Set `confidence` honestly per `kb/conventions.md`.
>   3. Cite the source line ranges you read in the `## Analysis` section.
>
> When the scope is exhausted (or the budget is spent):
>   1. Run `zanackb validate` and fix any errors before stopping.
>   2. Fill in the sprint's `## Summary` section: what was added, what is
>      still uncertain, and at least one candidate for the next sprint.
>   3. Flip `status:` to `done`.
>
> Report back with a one-paragraph summary, the list of new/updated KB
> files, and the proposed next sprint.

## Sprint file template

```markdown
---
id: "NNNN"
status: open
range: 0xNNNN-0xNNNN
strategy: bios_call_survey | vector_table_walk | forward_from_caller | callgraph_leaf | data_table | pattern
budget_turns: 30
---

# Sprint NNNN — <short title>

## Goal
One paragraph. What question does this sprint answer?

## Inputs
- kb/symbols/...  (entries already known that this sprint builds on)
- source/zanac.asm lines AAA-BBB

## Verification plan
- Static: cross-references match the hypothesized purpose.
- Dynamic: openMSX breakpoint at 0xNNNN fires on <triggering event>.

## Summary (filled at end)
```

## Strategies (cheat sheet)

| Strategy              | When to use                                                     |
|-----------------------|-----------------------------------------------------------------|
| `bios_call_survey`    | Early. Walks every `call`/`jp` into `0x0000-0x3FFF`.            |
| `vector_table_walk`   | Find VBLANK/HKEYI/HTIMI patches and the routines they install.   |
| `forward_from_caller` | Pick an already-known routine and decode the things it calls.    |
| `callgraph_leaf`      | Pick the smallest still-unknown routine. Quick wins.             |
| `data_table`          | Find `ld hl, NNNN` then table reads; identify the table shape.   |
| `pattern`             | Apply a known structure (e.g. PSG track player) to siblings.     |
