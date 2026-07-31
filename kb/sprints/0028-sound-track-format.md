---
id: "0028"
status: done
range: 0x4F4A-0x4F4A,0x5099-0x50D2,0x5182-0x5199,0x51E6-0x51E6,0x5208-0x520E,0x52E2-0x59D7
strategy: live_debug
budget_turns: 30
---

# Sprint 0028 — Sound track command format

## Goal

Sprint 0020 established the PSG sound engine architecture:

- **`psg_sound_tick`** (0x4E7B) — per-frame ISR entry; updates shadow PSG
  registers at 0xE201–0xE20B and flushes to hardware (AY-3-8910 at 0xA0–0xA2).
- **5 voice slots** at 0xE20C (stride 27 bytes), each driven by two sequencer
  routines: `sub_5099` (note sequencer) and `sub_50D2` (amplitude envelope).
- **27-entry event pointer table** at 0x5234/0x5236; `play_sound_event(A)` indexes
  into it to start a track.
- **Track data** packed at ~0x52E2–0x59D7, with note values 0x19–0x4x interleaved
  with command bytes 0x80–0xEF. Format was not decoded.

This sprint decodes the command byte format by correlating the byte stream with
live PSG register writes, then documents the full track format in
`kb/guides/sound-engine.md`.

## Inputs

- `kb/symbols/0x4000-init/sub_4e7b.md` — full architecture; sub_5099 / sub_50D2
  confirmed as note and amplitude sequencer
- `kb/guides/sound-engine.md` — architecture reference (sprint 0020)
- Event table at 0x5234 (confirmed), 27 events; event 3 = title music (0x543C)

## Verification plan

### Step 1 — Instrument sub_5099 with a PSG watchpoint

```python
with ZanacGame.launch() as game:
    msx = game.client
    game.wait_for_title()   # title music (event 3) plays from cold start

    # Capture PSG register writes for 1 second
    msx.cmd("set ::psg_log {}")
    wp = msx.cmd(
        "debug set_watchpoint write_io 0xa0 {} "
        "{lappend ::psg_log [list [reg PC] [reg A]]}"
    )
    time.sleep(1.0)
    msx.cmd(f"debug remove_watchpoint {wp}")
    log_raw = msx.cmd("set ::psg_log")
    # log_raw = list of {pc reg_idx} pairs
```

### Step 2 — Correlate with track data stream

For each PSG write at PC=X, read the voice slot that triggered it:
find which slot's `sub_5099` call produced that write, read IX+0x06/0x07
(stream pointer) and (IX+0x00) (current command byte). This maps command bytes
to PSG register effects.

### Step 3 — Static decode of sub_5099 and sub_50D2

Read ROM at 0x5099–0x50D0 and 0x50D2–0x50FF; decode the note sequencer and
envelope state machine. Expected to confirm:
- Low bytes (0x00–0x7F or 0x19–0x4x): note values → PSG frequency dividers
- 0x80–0xBF: control commands (loop, end, rest, tie, etc.)
- 0xC0–0xEF: envelope / volume commands
- 0xF0–0xFF: timing / tempo

### Step 4 — Decode one complete track

Starting at 0x543C (title music, event 3): parse the N-voice header, then
follow each voice stream until a track-end marker, documenting every command
encountered. Write the decoded sequence as a human-readable "score" in the
sprint summary.

## Focus questions

- What byte values mark "end of track" and "loop to position X"?
- How are note durations encoded — as separate timing commands or as note length in the note byte?
- Does the envelope follow ADSR, or is it a simpler fixed-shape per instrument?
- Are SFX (event ≠ 3) structurally different from music tracks?

## Additional KB entries required (open-ref cleanup)

The following routines have no KB entries and are called by already-documented
sound-system symbols.  They must be added as symbol files during this sprint,
using static analysis only (no openMSX needed for the stubs):

| Address | Parent context | Purpose (hypothesis) |
|---------|---------------|----------------------|
| 0x4F4A | `psg_sound_tick` (sub_4e7b) | Internal branch — note-sequencer sub-step |
| 0x5099 | `psg_sound_tick` | `sub_5099`: note sequencer (already in sprint goal) |
| 0x50D2 | `psg_sound_tick` | `sub_50D2`: amplitude envelope (already in sprint goal) |
| 0x5182 | `LAB_5178` | PSG helper — pre-step before sub_5099/sub_50D2 dispatch |
| 0x5199 | `play_sound_event` | Internal helper — channel-slot setup after event lookup |
| 0x51E6 | `init_psg_freq_table` | Helper — frequency table stride calculation |
| 0x5208 | `pause_handler` / `play_sound_event` | `mute_sound`: LD A,3 → (E200) |
| 0x520E | `pause_handler` | `restore_sound`: XOR A → (E200) |

## Expected output

- `kb/guides/sound-engine.md` extended with "Command byte reference" section.
- Sprint summary includes a partial decode of the title music track.
- KB symbol files for the 8 addresses in the table above.

## Summary (filled at end)

The sound track command format is fully decoded. The sprint's role hypotheses
for the two sequencer routines were **corrected**:

- **0x4F4A** = `advance_track_stream` — the actual **track command processor /
  note fetcher**. It defines the byte format.
- **0x5099** = `apply_amp_curve` — per-tick **volume-curve** (instrument
  envelope) modulator, *not* a note sequencer.
- **0x50D2** = `output_slot_to_psg` — per-voice **PSG output stage**.

### Command byte format

Per-voice streams mix **notes** (0x00-0x7F), **commands** (0x80-0x8C),
**note-replay** (0xDF-0xFF) and **duration tokens** (≥0xDF following a note).
Notes carry an optional duration token; duration is in sub-steps, and note
length in frames = duration × tempo (slot[0x04]).

Focus-question answers:

- **End of track / loop:** `0x82` = END (stop voice). `0x80 LL HH` = JUMP
  (unconditional, used for loop-to-start). `0x81 LL HH` = counted LOOP
  (decrement slot[0x0F], jump while ≠0).
- **Durations** are encoded as a separate token *after* the note byte; tokens
  0xE0-0xF2 index the duration table at 0x526C, 0xDF takes a raw count, and a
  missing token reuses the previous duration. A note's pitch and length are
  thus independent.
- **Envelope** is two-layer: a fixed-shape per-tick **volume curve** chosen by
  `SET_CURVE` (0x84, table 0x527D — 7 decay/attack-decay shapes) *plus* an
  optional linear **VOL_ENV ramp** (0x8B ceiling+rate). Not classic ADSR.
- **SFX vs music** share the same header + stream format, slot pool and engine;
  they differ only in which channels/curves/durations they use (SFX are short,
  often single-voice with noise mode and pitch slides).

Full command table, slot layout, duration table and volume curves are
documented in `kb/guides/sound-engine.md` § "Track command format".

### Title music (event 3 @ 0x543C) — decoded

Header: 3 voices, all tempo 2.

| Voice | Slot   | Ch | Amp | Curve | Stream |
|-------|--------|----|-----|-------|--------|
| 0     | 0xE242 | A  | 0x0F | 7    | 0x5458 |
| 1     | 0xE25D | B  | 0x0F | 2    | 0x54DC |
| 2     | 0xE278 | C  | 0x0F | 1    | 0x550A |

- **Channel A (0x5458)** — lead/arpeggio melody: a long run of duration-3 notes
  over a `C3` pedal (`C4 C3 G3 C3 E3 C3 F3 C3 …`), modulating through C / Bb / F
  bass roots, ending `… 2F 2E 2C 2A` then `JUMP 0x5458` (loops forever).
- **Channel B (0x54DC)** — bass + noise drum (slot cfg 0x43, bit1 = noise on):
  `SET_NOISE 9`, `SET_LOOPCNT 0x0F`, `IDX_TRANSPOSE 0x54FB` (per-bar pitch table
  `00 00 FB 00 …`), a 4×`C2` + `C3 C2` riff inside a 15-iteration `LOOP`, then
  `F1 F3 F2 F4 / F4 F4`, `TRANSPOSE 7`, `JUMP 0x54DE`.
- **Channel C (0x550A)** — percussive hi-hat/click: `PITCH_SLIDE 01 FF`,
  `SET_LOOPCNT 0x10`, `VOL_ADJ 0x0F`, `C6 C6 / VOL_ADJ 0xFF` (volume decays
  each step) inside a 16-iteration `LOOP`, then `JUMP 0x550D`.

### Live verification

Launched the title and read the three voice slots after playback started. Slot
contents matched the statically decoded header exactly (cfg/amp/curve/tempo/
chan/ptr), stream pointers advanced frame-by-frame, and channel C's amplitude
had decayed from 0x0F → 0x09 — directly confirming the `VOL_ADJ 0xFF` (−1) loop.
Note names decode to coherent musical phrases (clean scales, octave-12 spacing),
confirming the note→pitch mapping.

### Deliverables

- 8 symbol files: `advance_track_stream` (0x4F4A), `apply_amp_curve` (0x5099),
  `output_slot_to_psg` (0x50D2), `mute_psg_channels` (0x5182),
  `load_sound_event` (0x5199), `lookup_word_table` (0x51E6),
  `mute_sound` (0x5208), `restore_sound` (0x520E).
- `kb/guides/sound-engine.md` extended: command byte reference, duration table,
  volume curves, full 27-byte slot layout, full event pointer table; resolved
  the sprint-0020 open questions.
- `zanackb validate`: 0 errors; no warnings from the new entries.

Tool: `tools/decode_track.py` (track-stream disassembler).
