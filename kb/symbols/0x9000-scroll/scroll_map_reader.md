---
address: 0x9888
kind: routine
name: scroll_map_reader
confidence: likely
calls:   [0x95A8, 0x95ED, 0x986E, 0x9B22]
called_by: [0x97e3]
tags: [scroll, level-map, tile]
sprint: "0056"
---

# scroll_map_reader

## Summary
The per-column **tile assembler**: converts the active map-stream slots into the
24-byte tile-row buffers consumed by `scroll_vram_write`. Called once per built
column from [[scroll_precompute]] (0x97E3), which is itself reached from the
[[map_script_step]] interpreter (0x94C3) on the non-command (tile-build) path.
Processes up to 8 active map-stream slots (at 0xE2E0, each 4 bytes), assembles
one tile column, and copies the result into the name-table write buffer at
(0xE715). Live-confirmed to run continuously under the row-trigger driver
(sprint 0056, `tools/scroll_confirm.py`).

> **Distinct from the command interpreter.** 0x9888 only *renders* tiles from
> already-loaded stream slots; the script commands that *load/modify* those
> slots live in [[map_script_step]] (0x94C3) and [[level_script_format]].

## Stream-slot run lengths 0xFE and 0xFF differ (2026-07-30)

In the stream-slot pass, each slot emits `[delta][len][len tiles]` into the
assembly row. A `len` of 0xFE or 0xFF is not a run at all but an escape: 0x9A40
branches to 0x9A68, which calls [[load_stream_slots]] with `HL` pointing just
past the `len` byte and `C = (IY+0)` as the column base.

The two values then part company, and the distinction is easy to miss because it
rides on a flag saved across the call:

```
9A3E  CP 0xFE                ; sets Z only when len == 0xFE
9A40  JR NC, 9A68
...
9A6B  PUSH AF                ; carries that Z across load_stream_slots
9A6E  CALL 0x95A8
9A73  POP AF
9A74  JR NZ, 9A44            ; len == 0xFF -> normal bookkeeping
9A76  POP BC
9A77  JR 9A54                ; len == 0xFE -> skip it entirely
```

The skipped bookkeeping at 0x9A44 is `(IY+2/3) = cursor`, `DEC (IY+1)` and the
self-disable. Skipping it matters because `load_stream_slots` may have just
**reinitialised this very slot** — writing the pre-call cursor and timer back
over it would clobber the fresh configuration, leaving the slot replaying one
run on every subsequent row. The visible symptom is a stripe of tiles frozen
down the full height of the playfield while the rest of the terrain scrolls
normally.

So: **0xFE = replace the slot set and abandon this slot's old state; 0xFF = load
more slots and carry on.**

One more subtlety on the 0xFF path (it bit the web port, 2026-07-30): the
bookkeeping at 0x9A44 stores `(IY+2/3) = HL` **as `load_stream_slots` left
it** - i.e. advanced past every consumed slot record - not the pre-call
cursor. Write the pre-call cursor back instead and the next row reparses those
record bytes as `[delta][len][tiles]`, spraying ASCII-range garbage tiles
across the playfield.

## Analysis
Source lines 3997–4268.

### sub_9888 (0x9888): per-row tile-table selection
Selects tile-block table pointers from `(0xE702)` — the **scroll-row counter**,
not a stage index. `(0xE702) & 0x3` picks one of 4 primary blocks (0xA444 + n×32)
and `(0xE702) & 0x7` picks one of 8 variant blocks (0xA4A4 / 0xA564 + n×24), so
the background tile graphics cycle by row phase as the map scrolls:
- 0xE2AE ← pointer into 0xA444 table (primary tile IDs per stage)
- 0xE2B0 ← pointer into 0xA4A4 table (tile variant A)
- 0xE2B2 ← pointer into 0xA564 table (tile variant B)
- Resets IX scroll fields; initialises 0xE71A ← 0xEA40 (tile lookup base)

### LAB_98d4 (0x98D4): outer map-stream loop (4 streams, IY = 0xE2C0)
Each stream entry (8 bytes at IY) describes one "column group" of background
tiles. Calls `load_stream_slots` (0x95A8) to activate inner stream slots for
incoming ground-structure tile columns, then updates tile-count fields. Advances
stream pointer and loops B=4 times.

### LAB_99fd (0x99FD): inner stream loop (8 entries, IY = 0xE2E0)
Each 4-byte entry:
- IY+0: status (0x80=inactive, bit6=timing, else tile-data)
- IY+1: frame-timer countdown
- IY+2:3: 16-bit pointer into tile data stream

Per iteration: reads tile from pointer, looks up in 0xEA40 table, writes to
target position; advances pointer; updates timer. Handles special cases
(0xFE/0xFF markers). At end of all 8 entries: LDIR 24 bytes from 0xEA48 to
(0xE715) — commits the assembled tile row to the DMA buffer.

### sub_986e (0x986E): tile column extractor
Copies one vertical column of tiles (24 tiles × stride 24) from a source
buffer into 0xE800. Decoded as a standalone entry in [[copy_tile_column]]
(sprint 0033): in the credits path it reveals the 0xEB00 logo screen into the
live 0xE800 buffer one symmetric column-pair per frame.

## Key data addresses
| Address | Role |
|---------|------|
| 0xE702 | Scroll-row counter (low bits select per-row tile-block phase; round/stage = 0xE701) |
| 0xE2AE | Level tile-table pointer (primary) |
| 0xE2B0 | Level tile-table pointer (variant A) |
| 0xE2B2 | Level tile-table pointer (variant B) |
| 0xE2C0 | 4-entry column-group stream table (8 bytes each) |
| 0xE2E0 | 8-entry tile-stream table (4 bytes each = 0xE2E0–0xE2FF) |
| 0xEA40 | Row assembly buffer (32 bytes; write cursor kept in 0xE71A). Was described here as a 192-byte "tile lookup table" — see [[scroll_state]]. |
| 0xEA48 | Visible slice of that buffer: the 24 tiles committed to (0xE715) at 0x9A5B |
| 0xA444 | ROM primary tile table (level-indexed) |
| 0xA4A4 | ROM tile variant A table |
| 0xA564 | ROM tile variant B table |
