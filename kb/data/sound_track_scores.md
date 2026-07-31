---
address: 0x5236
end: 0x5A10
kind: data
name: sound_track_scores
confidence: confirmed
sprint: "0064"
tags: [sound, psg, music, sfx, track-data, o-sound]
---

# Sound-track scores — byte-exact decode (0x5236–0x5A10)

> Closes the last content gap in subsystem [[O-sound-system]]: **100 % of the
> music-data region is now accounted for as known tokens.** `tools/decode_tracks.py`
> walks all 27 events / 51 voices from the pointer table (0x5234) with the exact
> grammar of `advance_track_stream` (0x4F4A) and `load_sound_event` (0x5199),
> and the union of every consumed byte + engine tables + padding **== 0x5236–0x5A10
> with zero gaps and zero unknown opcodes**. Live-verified against the title
> music (see below).

## Coverage result

- Region **0x5236–0x5A10** = 2011 bytes → **2011/2011 covered (100.0 %)**, 0 gaps.
- Every stream byte classifies as a known token: 14 opcode classes seen
  (notes, replays, commands 0x80–0x8C — the full set).
- No stream escapes the region; every `0x80/0x81/0x83` jump target and every
  `0x8A` table pointer lands inside it.
- **Note:** the sprint's stated endpoint `0x5A11` overshoots by one — `0x5A11`
  is already code (`CD` = `CALL 0x46BC`). Track data ends at 0x5A10.

### What the region contains (byte accounting)

| Range | Bytes | Content |
|-------|-------|---------|
| 0x5234–0x526B | 56 | event pointer table (entries 0–27; 0 = sentinel) |
| 0x526C–0x527C | 17 | note-duration table (indexed by `0xE0`-token) |
| 0x527D–0x52E1 | 101 | volume-curve selector + curves 1–7 (`apply_amp_curve` 0x5099) |
| 0x52E2–0x5A0E | — | the 27 events' headers + voice streams |
| 0x53AD, 0x542A/0x542C, 0x54FB, 0x5764, 0x593F, 0x5958 | 7 tables | per-loop **IDX_TRANSPOSE** tables (targets of `0x8A`) |
| 0x5A0F–0x5A10 | 2 | trailing `FF FF` padding before code |

The 7 IDX_TRANSPOSE tables are the only "data-not-stream" bytes embedded *inside*
the event area; each is pointed to by an `0x8A LL HH` command and indexed by
`slot[0x0F]-1` (the loop counter), so it holds one transpose delta per loop
iteration (e.g. ev1 voice1's table @0x53AD = `00 FF 00 05 00 03 00 00`).

## Per-event map (all verified)

Voice count / channels match the sprint-0057 catalogue. `ch` = PSG channel
(slot[0x05]); stream = each voice's start pointer.

| Ev | Addr | V | ch | Streams | Kind (0057) |
|----|------|---|-----|---------|-------------|
| 1 | 0x52E2 | 3 | 0,2,1 | 52FE,538F,53B5 | main stage theme |
| 2 | 0x53D1 | 2 | 0,2 | 53E4,540D | round≡0 theme |
| 3 | 0x543C | 3 | 0,1,2 | 5458,54DC,550A | **title music** |
| 4 | 0x551C | 3 | 0,1,2 | 5538,5563,557F | game-over |
| 5 | 0x5599 | 2 | 0,1 | 55AC,55C5 | jingle (←ev12) |
| 6 | 0x55E6 | 1 | 1 | 55F0 | weapon SFX |
| 7 | 0x55FE | 3 | 0,1,2 | 561A,562A,5639 | stage intro → **ev1** |
| 8 | 0x5660 | 2 | 0,1 | 5673,567F | state jingle |
| 9 | 0x568B | 2 | 0,1 | 569E,56AE | state jingle |
| 10 | 0x56BE | 3 | 0,1,2 | 56DA,5750,5785 | round-variant BGM |
| 11 | 0x5799 | 3 | 0,1,2 | 57B5,**57B5**,57BD | init jingle (2 voices share stream 0x57B5) |
| 12 | 0x57CF | 3 | 0,1,2 | 57EB,**57EB**,57F7 | round/boss → **ev5** (2 voices share 0x57EB) |
| 13 | 0x5807 | 1 | 2 | 5811 | shot SFX |
| 14–24 | 0x5817–0x58EA | 1 | 2 (24=ch1) | … | SFX (ch C / noise) |
| 25 | 0x58FA | 3 | 0,1,2 | 5916,5944,5962 | round fanfare |
| 26 | 0x597E | 3 | 0,1,2 | 599A,59A7,59B2 | round-clear fanfare |
| 27 | 0x59D7 | 3 | 0,1,2 | 5A03,59FB,59F3 | round-clear variant |

- **Chains (`0x87 PLAY_EVENT`)** found by the walk: **ev7 → ev1** (@0x565D) and
  **ev12 → ev5** (@0x5804) — matching the live-confirmed 0057 catalogue.
- **Shared-stream voices:** ev11 and ev12 each allocate two slots (different D)
  pointing at the *same* stream, i.e. the same score doubled onto two PSG
  channels (a chorus/detune device).

## Format edge cases confirmed against the parser

Derived from `advance_track_stream` (0x4F4A) — byte-exact operand lengths:

- **Note (0x00–0x7F)** = 1 byte, **plus** a duration token *only if the next
  byte ≥ 0xDF*; otherwise it reuses `slot[0x0D]` (last duration) and consumes
  nothing more. `0x5086` does the `INC DE` past the note, then `0x503C` peeks
  the next byte to decide.
- **Duration token:** `0xE0–0xFF` → 1 byte, index `token-0xE0` into the table at
  0x526C; **`0xDF` → 2 bytes** (0xDF + a raw duration byte). Same rule for
  **REPLAY (0xDF–0xFF)** at the top level (replays `slot[0x0B]`).
- **Command operand lengths** (jump table @0x4F6C):
  `0x80 JUMP`/`0x81 LOOP`/`0x83 JMP_IF_ENV`/`0x8A IDX_TRANSPOSE`/`0x8B VOL_ENV`/
  `0x8C PITCH_SLIDE` take **2**; `0x84 SET_CURVE`/`0x85 TRANSPOSE`/`0x86 VOL_ADJ`/
  `0x87 PLAY_EVENT`/`0x88 SET_LOOPCNT`/`0x89 SET_NOISE` take **1**;
  `0x82 END` = **0** (voice terminator). `0x8D–0xDE` are unused (would index
  past the jump table) — **none occur** in the data.
- **Voice terminators:** every voice stream ends either at `0x82 END` or loops
  via an unconditional `0x80 JUMP` back to its body (all 51 verified).

## Live verification (title music, `tools/verify_tracks_live.py`)

Breakpointed the note handler (0x5030) on the title screen (auto-plays ev3) and
logged the note byte + slot without halting the CPU. The captured slot-0xE242
(ev3 voice 0) sequence is an **exact 23-note contiguous match** of the static
decode (found at loop offset 12 — the capture simply began mid-loop). Combined
with the statically-confirmed ev7→ev1 / ev12→ev5 chains, this closes goal 4.

## Tools

- `tools/decode_tracks.py` — `(no args)` coverage report + chains;
  `--score N` / `--score all` human-readable per-voice score.
- `tools/verify_tracks_live.py` — live note-stream spot-check (title music).
