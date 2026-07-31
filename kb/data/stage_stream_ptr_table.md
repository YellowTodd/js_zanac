---
address: 0x945C
end: 0x946D
kind: data
name: stage_stream_ptr_table
confidence: confirmed
sprint: "0045"
tags: [round, level-data, level-transition]
---

# stage_stream_ptr_table

## Summary

Nine 16-bit little-endian pointers to the **stream-start address** of each
round's level data, used both forwards and backwards:

- **`title_screen_init` (0x426A)** indexes it by `8 − E701` to pick the starting
  stream pointer when a game begins (E701 = chosen round 1–8).
- **`resolve_round_from_ptr` (0x9444)** searches the first 8 entries to convert a
  stream pointer back into a round number during stage transitions.

## Entries

| Index | Addr | Pointer | Round |
|-------|------|---------|-------|
| 0 | 0x945C | 0xB7A5 | 8 |
| 1 | 0x945E | 0xB61A | 7 |
| 2 | 0x9460 | 0xB3FD | 6 |
| 3 | 0x9462 | 0xB1DE | 5 |
| 4 | 0x9464 | 0xAF1F | 4 |
| 5 | 0x9466 | 0xAD61 | 3 |
| 6 | 0x9468 | 0xAAEF | 2 |
| 7 | 0x946A | 0xA751 | 1 |
| 8 | 0x946C | 0xA65C | (ending / round-0 stream start) |

Entry *i* is round `8 − i`. The round level streams therefore occupy
0xA751–0xB7A5 (round 1 lowest, round 8 highest); the 9th pointer 0xA65C is the
ending stream, below round 1, so `resolve_round_from_ptr` returns 0 for anything
under 0xA751 (e.g. the ending pointer 0xA6F4).

## Confidence

`confirmed` — values read directly from ROM; `resolve_round_from_ptr` round
mapping verified live for all entries (sprint 0045, `tools/sprint0045_verify.py`).

## See also

- `resolve_round_from_ptr.md` — 0x9444, the reverse lookup.
- `round-progression.md` (guide) — round advance + end-of-game.
