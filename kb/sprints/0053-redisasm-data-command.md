---
id: "0053"
status: done
range: 0x77ea-0x7826,0x79b7-0x79be,0x7af7-0x7b07,0x7b7b-0x7beb,0x7e68-0x7e78
strategy: tooling
budget_turns: 15
subsystems: [G]
---

# Sprint 0053 — `redisasm data` (code→DB) + fix the byte-neutral tables

## Goal

Add reverse-direction tooling to `tools/redisasm.py` and use it to fix the
remaining enemy-handler data tables that displayed as mis-decoded instructions in
`source/zanac.asm` (the deferred item from groups 1–2).

## Work

### New `redisasm data` subcommand (inverse of `patch`)

`data --before R --after R --start A --end A [--label N]` replaces mis-decoded
instruction lines for `[start, end)` with a labelled `DB` block, and
re-disassembles (via openMSX) any code the greedy data decode straddled — in
particular the **absorbed leading opcode byte** of the routine that follows the
table. openMSX is launched only when there is such code (`end < after_addr`).

### Tables converted (ROM byte-identical)

| Run | Region | Label | Absorbed entry re-decoded |
|-----|--------|-------|---------------------------|
| A | 0x77ea–0x7825 | `proto_box_type_table` (+ proto_box_sat_table) | 0x7826 box `BIT 7,(IX+0)` ✓ |
| B | 0x79b7–0x79bd | `umber_burst_param_table` | — (no absorption) |
| C | 0x7af7–0x7b06 | `base_spawner_spawn_table` | 0x7b07 teruzo `BIT 7,(IX+0)` ✓ |
| D | 0x7b7b–0x7bea | `teruzo_motion_tables` | — (no absorption) |
| E | 0x7e68–0x7e77 | `edge_swooper_a_anim` (+ edge_swooper_b_anim) | — (no absorption) |

## Summary

**Done ✓.** `redisasm data` added + documented (`kb/guides/redisasm-protocol.md`
Step 2c). 5 contiguous data runs (7 KB tables) converted to labelled `DB`;
`redisasm verify` **ROM byte-identical**. Corrected two KB notes that had wrongly
claimed `DD` absorption for the umber (B) and teruzo (D) tables — only the box (A)
and base-spawner (C) tables actually absorbed the following handler's entry.
`zanackb validate` 0 errors.
