---
id: "0064"
status: done
range: 0x5236-0x5A11
strategy: pattern
budget_turns: 25
subsystems: [O]
---

# Sprint 0064 — Byte-exact sound-track score decoder

> **Completion-plan sprint 3/6.** Subsystem [[O-sound-system]] is catalogued
> (27 events, purposes, chaining — sprint 0057) but the ~2011 bytes of track
> data have never been mechanically decoded end-to-end. This sprint closes the
> last O content gap by proving every byte is a known track command.

## Motivation

The track *command format* is documented (sprint 0028: note/duration encoding,
control bytes, the `0x87` chain command) and the 27-event pointer table at
0x5234 is confirmed. What's missing is the proof that the format accounts for
**every byte** of 0x5236–0x5A11 — i.e. that there are no unknown opcodes, no
unreferenced gaps, and no embedded data the format doesn't explain. Under the
100% criterion, "catalogued" isn't enough; "decoded byte-exactly" is.

## Goal

1. Write `tools/decode_tracks.py`: walk all 27 events from the pointer table
   (0x5234), following each voice/track stream to its terminator, applying the
   documented command grammar (notes, durations, control ops, `0x87` chaining,
   loops).
2. Assert **full coverage**: the union of all decoded streams == 0x5236–0x5A11
   with no gaps and no overlaps-with-disagreement; every opcode encountered is
   a known command. Any residual bytes → investigate (padding? unreferenced
   track? unknown op?) and document.
3. Emit a human-readable score per event (notes/rests per channel) — this is
   the per-track "content" the O overview lists as the remaining gap.
4. Spot-check 3 events against live PSG register writes (e.g. ev1 main theme,
   ev18 explosion, one chained pair like ev7→ev1).

## Inputs

- [[sound-engine]] guide (PSG engine 0020 + track command format 0028 + event
  catalogue 0057)
- Event pointer table 0x5234; `kb/symbols/0x5000-gameplay/` sound entries;
  sound engine at 0x8BF5 (`LAB_ram_8bf5`, patched block)
- `kb/guides/psg-ay-3-8910.md`
- source/zanac.asm — the 0x5236–0x5A11 DB run (read bounded ranges only)

## Verification plan

- Static: decoder covers 100% of the range with known opcodes; chain targets
  (`0x87`) match the documented ev7→1 / ev12→5 pairs.
- Dynamic: openMSX breakpoint on the PSG write helper while playing a decoded
  event; logged register stream matches the decoded notes for the first bars.
- Run `tools/coverage_audit.py` (0063): the region flips to fully accounted.

## Expected KB entries

- `kb/data/sound_track_scores.md` — per-event decoded content summary + format
  edge cases found.
- Update `kb/guides/sound-engine.md` (link the decoder, note any new opcode
  semantics).
- `tools/decode_tracks.py`.

## Summary (filled at end)

**Done — 100 % byte coverage.** `tools/decode_tracks.py` walks all 27 events /
51 voices from the pointer table (0x5234) using the exact grammar re-derived
from `advance_track_stream` (0x4F4A) + `load_sound_event` (0x5199): the command
jump table is at **0x4F6C**, operand lengths `0x80/81/83/8A/8B/8C = 2`,
`0x84–0x89 = 1`, `0x82 END = 0`; notes carry a duration token only when the
next byte ≥ 0xDF (`0xDF` = +raw byte, `0xE0–0xFF` = duration-table index),
REPLAY = 0xDF–0xFF. Full result in [[sound_track_scores]].

- **Goal 1 (decoder):** done — DFS over each voice's control flow (following
  JUMP/LOOP/JMP_IF_ENV, terminating at END), collecting every consumed byte.
- **Goal 2 (full coverage):** the union of stream bytes + engine tables
  (duration 0x526C–0x527C, curves 0x527D–0x52E1) + 7 embedded IDX_TRANSPOSE
  tables (0x8A targets) + `FF FF` tail padding == **0x5236–0x5A10 with 0 gaps,
  0 unknown opcodes** (no `0x8D–0xDE`, no stream escaping the region). Corrected
  the region end: **0x5A11 (`CD`) is code** (`CALL 0x46BC`), not track data —
  the sprint range overshot by 1.
- **Goal 3 (human score):** `--score N` prints per-voice note/command streams;
  the main theme (ev1) and title music (ev3) read as coherent melodies.
- **Goal 4 (dynamic spot-check):** `tools/verify_tracks_live.py` breakpointed
  the note handler (0x5030) on the title screen; the live slot-0xE242 note
  stream is an **exact 23-note contiguous match** of the ev3-voice0 static
  decode (loop offset 12). Chains **ev7→ev1** and **ev12→ev5** found statically
  (match the 0057 live catalogue).
- **Audit:** `tools/coverage_audit.py` known% rose **81.5 → 87.66**; the
  0x5236–0x5A11 region is gone from the unknown list (remaining unknowns all
  owned by 0065/0066).

**Findings of note:** ev11 & ev12 each allocate **two slots sharing one stream**
(the same score doubled onto two PSG channels); the 7 IDX_TRANSPOSE tables are
the only data-not-stream bytes inside the event area.

New/changed: `tools/decode_tracks.py`, `tools/verify_tracks_live.py`,
`kb/data/sound_track_scores.md` (new), `kb/guides/sound-engine.md`.
