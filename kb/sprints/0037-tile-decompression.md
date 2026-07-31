---
id: "0037"
status: done
range: 0x5C07-0x5D1A
strategy: forward_from_caller
budget_turns: 15
subsystems: [E]
---

# Sprint 0037 — Tile loading and decompression pipeline

> **Subsystem slice:** [[E-level-data-and-decompression]] — close 0037 when the
> E slice develops the decompressor internals.

## Goal

Document the sub-routines inside the 0x5Cxx–0x5Dxx tile-loading / decompression
block that are called by documented symbols but have no KB entries:

1. **`SUB_5C07`** (0x5C07) — internal sub-routine called by `decompress_block`
   (0x5C60).  Hypothesis: handles one decompression step — reads a compressed
   byte, unpacks it, writes output tiles.
2. **`SUB_5C28`** (0x5C28) — called by `title_intro_seq` (0x5A11); sits in the
   middle of the decompress area.  Hypothesis: a VRAM tile-write helper used
   during the title animation to stream tiles sequentially.
3. **`SUB_5C2E`** (0x5C2E) — called by `decompress_block`; hypothesis: handles
   the RLE/copy-run inner loop, or the "write N repeated bytes" path.
4. **`SUB_5D1A`** (0x5D1A) — called by `decompress_block`; hypothesis: the
   "copy from source" path — non-RLE literal sequence.

All four are in the same continuous decompression routine block.  Sprint 0010
(or similar) documented `decompress_block` as the entry; this sprint adds the
internal helpers.

## Inputs

- `kb/symbols/0x5000-gameplay/decompress_block.md` — entry at 0x5C60; calls to
  0x5C07, 0x5C2E, 0x5D1A
- `kb/symbols/0x5000-gameplay/title_intro_seq.md` — calls 0x5C28
- Source lines 2680–2900 (0x5C07–0x5D50 range; full decompression block)

## Verification plan

### Step 1 — Read the full decompression block (static)

Read source lines 2680–2870 to map the complete call graph:
- Which sub-entry points branch on the high bit of the compressed byte?
- Does 0x5C07 handle the "flag byte" test (compressed vs literal)?
- Does 0x5C2E or 0x5D1A handle the run-length copy?

### Step 2 — Identify 5C28 vs decompressor (static)

Read lines 2706–2720.  Determine whether 5C28 is truly a standalone VRAM
helper or whether it's a mid-decompressor entry point that can be reached
independently.  If it's only reachable as an inline target, document it as
`LAB_5C28` (data entry) rather than a `sub`.

### Step 3 — Map register conventions (static)

For each of the four addresses, identify:
- Input registers (HL = source ptr? DE = dest ptr? BC = count?)
- Output / modified state
- Whether they share a common "write byte to VRAM" inner call

## Key questions

- Is the compression format LZ77, RLE, or a custom scheme?  What is the flag
  bit layout in the compressed stream?
- Does 0x5C28 appear in any other caller beyond `title_intro_seq`?
- What does `decompress_block` expect in HL/DE/BC on entry?

## Expected KB entries

- `kb/symbols/0x5000-gameplay/decompress_step.md` — `SUB_5C07` (0x5C07)
- `kb/symbols/0x5000-gameplay/vram_tile_stream.md` — `SUB_5C28` (0x5C28, if standalone)
- `kb/symbols/0x5000-gameplay/decompress_run.md` — `SUB_5C2E` (0x5C2E)
- `kb/symbols/0x5000-gameplay/decompress_literal.md` — `SUB_5D1A` (0x5D1A)
- Update `decompress_block.md` with correct `calls` cross-refs

## Summary (filled at end)

Closed as the final slice of subsystem **E**. All four target addresses (plus
the string-print family interleaved with them) decoded statically; the 6
related validate warnings are resolved.

### The 0x5Cxx block is two families, not one

The routines between 0x5C07 and 0x5D2B are **two distinct families** that happen
to share the VDP-write primitive:

1. **Decompressor** — `decompress_block` (0x5CCF) + helpers:
   - **0x5C07 `vdp_write_byte`** — `OUT (C),A` to the VDP data port (raw sibling
     of the DI-guarded `vdp_write_byte_di` 0x5BFC). The output primitive.
   - **0x5D1A `decompress_unit`** — emit one copy/repeat unit: copy mode writes
     `A` once; repeat mode (`E` bit0) reads a count byte and writes `A` N times.
   - **0x5C2E** — this is the *already-documented* `dispatch_inline_table` (the
     generic computed-jump trampoline), not a decompressor-only helper. Enriched
     its `called_by` to show the dual use (decompressor 0x5CF5, map-script
     0x94E8, fire 0x7266/0x727C/0x74AB, enemy 0x8C1A/0x8D19).

2. **Inline VRAM string printer** (shared HUD/title/text util, *not* the
   decompressor):
   - **0x5C10 `vram_string_copy`** — DI-guarded copy of a 0x00-terminated string
     from HL to VRAM; HL ends past the terminator.
   - **0x5C1F `vram_print_inline`** — trampoline that prints the string inlined
     right after the `CALL` and resumes past it.
   - **0x5C25 `vdp_set_addr_write`** (pre-existing) — coordinate-prefix entry
     (`CALL 0x42ED`) that falls into 0x5C28.
   - **0x5C28 `vram_print_inline_hl`** (new; resolves the alt-entry warning) —
     `SETWRT HL` then print inline. Split out of the 0x5C25 doc so the 13
     direct callers (title text, ROUND banner) resolve by exact address.

### Format answer (key question)

The compression is a **custom RLE with an escape byte and a mode toggle** (fully
matching `xtra/zanac-decoder.py`): single-special = toggle copy/repeat,
double-special+{00,01,02} = STOP / SET-SPECIAL / MULTI. Not LZ77. Already
captured in `decompress_block.md`; this sprint added the leaf helpers.

### Deliverables

- New symbols: `vdp_write_byte` (0x5C07), `decompress_unit` (0x5D1A),
  `vram_string_copy` (0x5C10), `vram_print_inline` (0x5C1F),
  `vram_print_inline_hl` (0x5C28).
- Re-scoped `vdp_set_addr_write` to 0x5C25–0x5C27; enriched
  `dispatch_inline_table` and `decompress_block` cross-refs.
- Also (subsystem-E completion, adjacent): extended `tile_tables` to 0xA653
  (the 0xA624/0xA63C fixed columns → 0xE2B4/0xE2B6), and added the new guide
  `kb/guides/level-data-block-map.md` carving the whole 0x9B64–0xBE27 level
  block into named sub-regions.
- `zanackb validate`: **0 errors**; 6 decompressor warnings cleared (88→82).
