---
address: 0x4F4A
end: 0x5098
kind: routine
name: advance_track_stream
confidence: confirmed
inputs: { IX: "sound-engine slot base (0xE20C + D*27)" }
outputs: { "slot[0x06/0x07]": "advanced stream pointer", "slot[0x12/0x13]": "target PSG period" }
clobbers: [AF, BC, DE, HL]
calls:   [0x51E6]
called_by: [0x4E7B]
tags: [audio, psg, sound-engine, track-format]
sprint: "0028"
---

# advance_track_stream

## Summary

**Track command processor / note fetcher.** Called from `psg_sound_tick`
(0x4EBD, via `CALL Z`) once a voice slot has played its current note for the
full duration (sub-step counter slot[0x09] reached slot[0x0a]). Reads the next
byte(s) from the voice's track stream (pointer in slot[0x06/0x07]) and acts on
them: plays a note, replays the previous note with a new duration, or executes
one or more **command bytes** (loop / jump / volume / envelope / slide / etc.)
before landing on the next note.

This is the routine that defines the **sound track byte format** — see
`kb/guides/sound-engine.md` § "Track command format".

## Dispatch (0x4F4A)

```
4F4A  LD E,(IX+6); LD D,(IX+7)   ; DE = stream read pointer
4F52  LD A,(DE)                  ; A = next byte
4F53  BIT 7,A
4F55  JP Z, 0x5030               ; 0x00-0x7F  -> NOTE (play_note, 0x5030)
4F58  CP 0xDF
4F5A  JP NC,0x501F               ; 0xDF-0xFF  -> REPLAY prev note w/ new duration
4F5D  INC DE; RES 7,A            ; 0x80-0xDE  -> COMMAND: A = cmd & 0x7F (index)
4F60  LD HL,0x4F51; PUSH HL      ; return addr = re-dispatch loop
4F64  LD BC,0x4F6C
4F67  CALL 0x51E6                ; HL = *(0x4F6C + 2*index)   command jump table
4F6A  LD A,(DE); JP (HL)         ; A = operand, jump to handler
```

Commands return to **0x4F51** (`INC DE; LD A,(DE); ...` re-enters the dispatch),
so a run of command bytes is consumed in a single call until a note (bit 7
clear) or a 0xDF-0xFF replay token is reached. Track-end (0x82) unwinds the
stack and jumps to 0x4ECD instead of returning.

## Command jump table (0x4F6C, word-indexed by `cmd & 0x7F`)

| Cmd  | Handler | Operands | Meaning |
|------|---------|----------|---------|
| 0x80 | 0x4F86  | LL HH    | **JUMP** — continue track at address HHLL (used for loop-to-start) |
| 0x81 | 0x4F8D  | LL HH    | **LOOP** — `--slot[0x0F]`; if ≠0 jump to HHLL, else fall through |
| 0x82 | 0x4F95  | —        | **END** — `slot[0]=0` (stop voice), unwind, jump 0x4ECD |
| 0x83 | 0x4FF3  | LL HH    | **JUMP_IF_ENV** — if play-flag bit1 (env target reached) clear → jump HHLL |
| 0x84 | 0x4F9E  | nn       | **SET_CURVE** — slot[0x02] = nn (volume-curve selector, table 0x527D) |
| 0x85 | 0x4FA2  | nn       | **TRANSPOSE** — slot[0x03] += nn (nn=0 resets to 0) |
| 0x86 | 0x4FB6  | nn       | **VOL_ADJ** — slot[0x01] += signed nn, clamp [0,15] |
| 0x87 | 0x5189  | nn       | **PLAY_EVENT** — call `play_sound_event(nn)` (spawn another track) |
| 0x88 | 0x4FAD  | nn       | **SET_LOOPCNT** — slot[0x0F] = nn (loop counter for 0x81/0x8A) |
| 0x89 | 0x4FB2  | nn       | **SET_NOISE** — slot[0x19] = nn (PSG noise period for noise mode) |
| 0x8A | 0x4FCE  | LL HH    | **IDX_TRANSPOSE** — slot[0x03] += table_HHLL[slot[0x0F]-1] (per-loop pitch) |
| 0x8B | 0x4FE2  | cc rr    | **VOL_ENV** — slot[0x16]=ceiling cc, slot[0x14]=rate rr, set play bit5 |
| 0x8C | 0x4FFC  | ff rr    | **PITCH_SLIDE** — slot[0x10]=rate rr; ff bit7=dir, ff&0x7F=shift→slot[0x17] |

Indices 0x0D-0x5E (cmd 0x8D-0xDE) fall past the 13-entry table into code and are
not used by any track.

## Note / duration path

- **Note (0x00-0x7F):** `play_note` (0x5030) stores the note in slot[0x0B],
  computes the PSG period via `0x5087` → slot[0x12/0x13], then peeks the next
  byte. **Duration encoding** (0x5048):
  - next byte ≥ 0xDF → it is a duration token; otherwise the previous duration
    (slot[0x0D]) is reused.
  - token 0xDF → the byte after it is a raw duration count.
  - token 0xE0-0xF2 → index `token-0xE0` into duration table at **0x526C**
    (`01 02 03 04 06 08 0C 10 18 20 30 40 60 80 C0 00 12 1C 24`).
  - duration (slot[0x0A]) is in **sub-steps**; each sub-step is slot[0x04]
    frames, so note length in frames = slot[0x0A] × slot[0x04].
- **Replay (0xDF-0xFF):** `0x501F` recomputes the period for the *previous*
  note (slot[0x0B]) and applies a new duration via the same 0x5048 path.

## Helpers

- **0x5086 / 0x5087** — note→PSG-period: `A=0` → period 0 (rest); else
  `A += slot[0x03]` (transpose), then word lookup in the precomputed frequency
  table at 0xF200 (built by `init_psg_freq_table`).

## Verification

Confirmed live (sprint 0028): title music (event 3) slots at 0xE242/0xE25D/
0xE278 advance their stream pointers frame-by-frame and the decoded streams
yield musically coherent note sequences (see sprint summary).
