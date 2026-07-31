# Sound Engine Architecture

## Overview

Zanac uses a VBlank-driven, shadow-register PSG sound engine. Music and SFX
share the same 5-voice slot table. The engine fully drives PSG registers 0–10
every frame (~59 Hz).

## Call chain

```
vblank_isr (0x43DA)
  └─ psg_sound_tick (0x4E7B)          ← per-frame tick
       ├─ [fire-sound fast path]
       │    └─ 0x5182 → GICINI(7, 0xBF)   mute all PSG channels, return
       ├─ for each of 5 slots (IX=0xE20C, stride 27):
       │    ├─ sub_5099                    advance note sequencer
       │    └─ sub_50D2                    update amplitude envelope
       └─ GICINI loop: write R0-R10 from shadow table 0xE201-0xE20B
```

Music tracks/SFX are enqueued via:
```
play_sound_event (0x5189)  [called by game code at any time]
  └─ sub_5199              look up event in table at 0x5234,
                           copy data into a free slot at 0xE20C
```

## Shadow PSG registers (0xE200–0xE20B)

The sound engine writes to shadow copies each frame; at frame end `psg_sound_tick`
flushes all 11 values to hardware via GICINI.

| Address | PSG Reg | Meaning |
|---------|---------|---------|
| 0xE200  | —       | Engine flags: bit 0 = fire-sound-pending; bit 1 = paused |
| 0xE201  | R0      | Ch A frequency fine |
| 0xE202  | R1      | Ch A frequency coarse |
| 0xE203  | R2      | Ch B frequency fine |
| 0xE204  | R3      | Ch B frequency hi |
| 0xE205  | R4      | Ch C frequency fine |
| 0xE206  | R5      | Ch C frequency hi |
| 0xE207  | R6      | Noise period |
| 0xE208  | R7      | Mixer (initialised 0xB8 = tone A-C on, noise off) |
| 0xE209  | R8      | Ch A volume |
| 0xE20A  | R9      | Ch B volume |
| 0xE20B  | R10     | Ch C volume |

PSG registers 11-13 (envelope) and 14-15 (I/O) are not updated by the main
sequencer loop; envelope is handled via MODUL bit per-slot.

### How `output_slot_to_psg` (0x50D2) drives the mixer

The tone bits are **never cleared**. `cfg` bit 5 re-seeds R7 with 0xB8 — all
three tones on, all three noises off (bits are active low) — and from there
0x50FE only ever touches the *noise* bits: the tone path ORs
`mixer_noise_off` (0x513C = `08 10 20`) to switch the channel's noise off, and
the noise path ANDs `mixer_noise_on` (0x5139 = `F7 EF DF`) to switch it on,
after copying slot `+0x19` into R6. A voice with no tone of its own is
silenced instead by `LD DE,0x0000` at 0x50FB, which writes a **period of 0**
rather than muting the channel; likewise a slot whose period is already zero
has its amplitude forced to 0 at 0x50F4.

The consequence matters for anything that renders this register image: Zanac's
percussion runs **tone and noise on the same channel**, and on the AY the two
gate one DAC, so the channel output is `tone AND noise`, never their sum. The
explosion (event 18) is the clearest case — R7 = 0x9B (channel C tone + noise),
R6 = 28-31, amplitude 15, with the tone period swept 3648 -> 489, i.e. the
noise chopped at 30 -> 229 Hz. Adding the two sources independently instead
puts a clean square at full level beside the noise, and the square is then what
you hear; see correction 74 in [[port-corrections]].

## Sound-engine slot table (0xE20C)

5 slots × 27 bytes each (stride 0x1B).

`stop_all_sound` (0x516C) clears slot[0] (active flag) of all 5 slots
and calls GICINI to reset hardware.

Full slot layout (confirmed, sprint 0028):

| Off  | Meaning |
|------|---------|
| 0x00 | voice-config flags: bit0 = tone output, bit1 = noise mode, bit5 = re-init mixer, bit6 = busy |
| 0x01 | base amplitude (0-15), modified by VOL_ADJ / VOL_ENV |
| 0x02 | volume-curve selector (index into 0x527D) |
| 0x03 | transpose (semitone offset added to note) |
| 0x04 | tempo (frames per sub-step) |
| 0x05 | PSG channel index (0=A, 1=B, 2=C) |
| 0x06-07 | track stream pointer (current read position) |
| 0x08 | play-flags: bit1 = vol-env target reached, bit5 = vol-env active, bit6 = slide dir, bit7 = pitch-slide active |
| 0x09 | sub-step counter (counts up to slot[0x0A]) |
| 0x0A | note duration (in sub-steps) |
| 0x0B | last note value (for REPLAY 0xDF-0xFF) |
| 0x0C | tick counter (counts down from slot[0x04]) |
| 0x0D | last duration (reused by notes with no duration token) |
| 0x0E | per-tick output amplitude (computed by apply_amp_curve) |
| 0x0F | loop counter (LOOP / SET_LOOPCNT / IDX_TRANSPOSE) |
| 0x10 | pitch-slide rate |
| 0x11 | pitch-slide accumulator |
| 0x12-13 | target PSG period |
| 0x14 | volume-envelope rate |
| 0x15 | volume-envelope accumulator |
| 0x16 | volume-envelope ceiling/target |
| 0x17 | pitch-slide shift amount |
| 0x18 | event/track number |
| 0x19 | noise period |
| 0x1A | volume-curve phase index |

## Event/track table (0x5234)

A 16-bit pointer table indexed by event number. Entry 0 is unused (sentinel).
Entries 1–27 occupy 0x5236–0x526B; **0x526C** begins the note-duration table.

`load_sound_event` (0x5199) selects entry A: `HL = *(0x5234 + A*2)`.

### Full event catalogue (sprint 0057)

Structure (voice count / channels) is **confirmed** from the ROM headers;
purpose is **likely**, derived from `play_sound_event` (0x5189) call sites.
Voices column: `V` = voice count; noise = cfg bit1 set. Trigger = the code that
calls the event.

| Ev | Addr | V | Kind | Trigger / purpose |
|----|------|---|------|-------------------|
| 1  | 0x52E2 | 3 | music | **Main stage theme** (longest, 239 B); reached via event 7's chain (live-confirmed) |
| 2  | 0x53D1 | 2 | music | Round-start theme for rounds ≡0 mod 8 (0x4065 else-path) |
| 3  | 0x543C | 3 | music | **Title music** (0x5A16, live-confirmed) |
| 4  | 0x551C | 3 | music | Game-over / attract (0x467B) |
| 5  | 0x5599 | 2 | jingle | Chained from event 12 (0x5804) |
| 6  | 0x55E6 | 1 | SFX | Weapon/fire (0x7260) |
| 7  | 0x55FE | 3 | music | **Round-start stage-theme intro** (0x4065, round&7≠0) → chains to event 1 (`0x87 01` @0x565D); live-confirmed |
| 8  | 0x5660 | 2 | jingle | State jingle, `E102` bit2 clear (0x4A61); also enemy (0x8763) |
| 9  | 0x568B | 2 | jingle | State jingle, `E102` bit2 clear (0x4A20) |
| 10 | 0x56BE | 3 | music | Round-variant BGM (0x4133 init) |
| 11 | 0x5799 | 3 | jingle | Init jingle (0x40EA) |
| 12 | 0x57CF | 3 | jingle | Round/boss (0x924B) → chains to event 5 (`0x87 05` @0x5804) |
| 13 | 0x5807 | 1 | SFX | **Shot fire SFX** (0x7234; event scales with shot state 0xE10F) — live-confirmed while shooting |
| 14 | 0x5817 | 1 | SFX | ch C |
| 15 | 0x5829 | 1 | SFX | ch C |
| 16 | 0x5844 | 1 | SFX | ch C noise — enemy (0x86C0) |
| 17 | 0x5859 | 1 | SFX | ch C noise — enemy hit (0x8495, 0x8B87) |
| 18 | 0x5869 | 1 | SFX | ch C noise — **explosion** (base damage/death 0x8879, 0x8E1F) |
| 19 | 0x5888 | 1 | SFX | ch C — fire (0x7516) / enemy (0x89FF) |
| 20 | 0x589F | 1 | SFX | ch C — player (0x7911) / base (0x8438) |
| 21 | 0x58AC | 1 | SFX | ch C — enemy hit (0x8025, 0x8209) |
| 22 | 0x58C0 | 1 | SFX | ch C noise |
| 23 | 0x58D2 | 1 | SFX | ch C — player (0x78C1) |
| 24 | 0x58EA | 1 | SFX | ch B — weapon (0x74C1, 0x74E2) |
| 25 | 0x58FA | 3 | jingle | Round fanfare, conditional (0x9044) |
| 26 | 0x597E | 3 | jingle | Round-clear fanfare, `C=0x1A` (0x917A) |
| 27 | 0x59D7 | 3 | jingle | Round-clear fanfare variant, `C=0x1B` (0x917A) |

Three mechanisms tie the table together (all live-confirmed, sprint 0057):

- **Round-start BGM** — at round start (0x405D–0x4065) the game plays **event 7**
  when `round & 7 ≠ 0`, else **event 2** (rounds ≡0 mod 8). Event 7 is the
  stage-theme intro that immediately **chains into event 1** (the long main
  theme). So the in-game music is *event 7 → event 1*.
- **Shot fire SFX** — the fire code at 0x7234 plays
  `event = 3 + ((0xE10F) >> 2)` and sets the voice transpose from `0xE10F`, so
  the shooting sound's pitch/event scales with the shot state byte `0xE10F`
  (loaded with `0xE10D`/`0xE10E` from a parameter block at 0x778B). Observed
  event 13 while shooting.
- **Track chaining** — the `0x87 nn` PLAY_EVENT command lets a track spawn
  another: **event 7 → event 1** and **event 12 → event 5**. Confirmed live: the
  event-1 call came from the sound engine itself (`advance_track_stream` 0x4F51),
  not game code.

## Track data format

Decoded in sprint 0028 (`advance_track_stream` 0x4F4A, `load_sound_event` 0x5199).

### Header (per event)

```
Byte 0:       N = number of voice entries
For each of N voices:
  Byte 0:     slot descriptor D  (slot = 0xE20C + D × 27)
  Bytes 1-8:  copied to slot[0..7]:
    slot[0] = voice-config flags (bit0 = tone out, bit1 = noise mode, bit6 = busy)
    slot[1] = base amplitude (0-15)
    slot[2] = volume-curve selector (table 0x527D)
    slot[3] = transpose (semitones)
    slot[4] = tempo (frames per sub-step)
    slot[5] = PSG channel (0=A, 1=B, 2=C)
    slot[6..7] = track stream start pointer
```

(The stride is **27** = 0x1B, matching `psg_sound_tick`/`stop_all_sound`;
the "× 26" in sprint 0019/0020 was a miscount — `load_sound_event` computes
D × 27 at 0x51A6.)

### Stream bytes (per voice)

Each voice's stream is parsed by `advance_track_stream` (0x4F4A) when the
current note finishes:

| Byte    | Meaning |
|---------|---------|
| 0x00-0x7F | **Note.** value → PSG period; `note = octave×12 + semitone + 1` (0 = rest). May be followed by a duration token (below); otherwise reuses previous duration. |
| 0x80-0x8C | **Command** (see table). |
| 0x8D-0xDE | unused (index past the command jump table). |
| 0xDF-0xFF | **Replay** previous note (slot[0x0B]) with a new duration token. |

**Duration tokens** (the byte following a note, if ≥ 0xDF):
- `0xDF` → the *next* byte is a raw duration count.
- `0xE0-0xF2` → index `token-0xE0` into the duration table at **0x526C**:
  `01 02 03 04 06 08 0C 10 18 20 30 40 60 80 C0 00 12 1C 24`.
- Duration is in **sub-steps**; note length in frames = duration × tempo (slot[4]).

### Command byte reference

All multi-byte addresses are little-endian. After a command runs, the parser
continues consuming bytes until it reaches a note or a 0xDF-0xFF replay token.

| Cmd  | Operands | Name | Effect |
|------|----------|------|--------|
| 0x80 | LL HH    | JUMP          | Continue track at HHLL (loop-to-start). |
| 0x81 | LL HH    | LOOP          | `--slot[0x0F]`; if ≠0 jump to HHLL, else continue. |
| 0x82 | —        | END           | Stop voice (`slot[0]=0`) and exit. |
| 0x83 | LL HH    | JUMP_IF_ENV   | If play-flag bit1 (vol-envelope target reached) is clear → jump HHLL. |
| 0x84 | nn       | SET_CURVE     | slot[0x02] = nn (volume-curve / instrument). |
| 0x85 | nn       | TRANSPOSE     | slot[0x03] += nn (nn=0 resets to 0). |
| 0x86 | nn       | VOL_ADJ       | slot[0x01] += signed nn, clamp [0,15]. |
| 0x87 | nn       | PLAY_EVENT    | `play_sound_event(nn)` — spawn another track/SFX. |
| 0x88 | nn       | SET_LOOPCNT   | slot[0x0F] = nn (loop counter). |
| 0x89 | nn       | SET_NOISE     | slot[0x19] = nn (PSG noise period for noise mode). |
| 0x8A | LL HH    | IDX_TRANSPOSE | slot[0x03] += table_HHLL[slot[0x0F]-1] (per-loop pitch). |
| 0x8B | cc rr    | VOL_ENV       | Volume ramp: ceiling cc, rate rr; enables play-flag bit5. |
| 0x8C | ff rr    | PITCH_SLIDE   | Portamento: rate rr, ff bit7=direction, ff&0x7F=shift. |

### Volume curves (instruments) — table 0x527D

`SET_CURVE`/slot[0x02] selects a per-tick amplitude shape read by
`apply_amp_curve` (0x5099). Curve byte 0x0F = full level, lower = attenuated,
0x80 = sustain-at-last-level marker. Curves 1-7 live at 0x528D-0x52E1
(decay / attack-decay / sustain shapes); selector 0 = flat.

## PSG frequency table (0xF200)

`init_psg_freq_table` (0x513F) precomputes 12 notes × 10 octaves = 120 entries
at 0xF200 (stride 0x19 bytes). Base frequencies from ROM table at 0x51F0.
The sequencer reads from here to set slot frequency registers.

## Fire-sound mechanism

When the Z key is pressed:
1. Player input handler sets 0xE200 bit 0.
2. Next VBlank: `psg_sound_tick` sees the flag, jumps to 0x5182.
3. 0x5182: `GICINI(7, 0xBF)` → all PSG channels muted for one frame.
4. The "click" / "zap" sound is produced by this brief mute followed by
   normal music resuming the next frame.

## Resolved (sprint 0028)

- **sub_5099** is `apply_amp_curve` (per-tick volume-curve modulator), **not** a
  note sequencer; **sub_50D2** is `output_slot_to_psg` (channel output stage).
  Note fetching / command parsing is `advance_track_stream` (0x4F4A).
- Slot descriptor D selects a 27-byte slot (`0xE20C + D×27`); the PSG channel
  A/B/C is a *separate* field, slot[0x05]. Title music uses D=2,3,4 → channels
  0,1,2. SFX share the same slot pool.
- Stride is **27** everywhere; the earlier "D×26" was a miscount.
- Command byte format fully decoded — see "Track command format" above.
- 27 events (index 1-27); event 0 is a sentinel. Note/duration/command bytes
  documented. Event pointers listed below.

## Stop-all-sound (0x516C)

`stop_all_sound` (0x516C — a misnomer; it only touches PSG) clears
slot[0] of all 5 voice slots and writes `WRTPSG(R7, 0xBF)` to mute the mixer.
Called at level load (`load_bg_level`) and round/boss transitions to cut music
before the next track starts. Confirmed sprint 0057.

## Resolved (sprint 0057)

- **All 27 events catalogued** (structure + purpose + chaining) — see the full
  table above. The 0028 "per-event purpose" question is closed.
- Round-start BGM = event 7 (or 2 on rounds ≡0 mod 8) → chains to event 1; the
  shot fire SFX is the **computed** `3 + (0xE10F >> 2)` (0x7234); tracks chain
  via `0x87` PLAY_EVENT (event 7 → 1, event 12 → 5). All live-confirmed.
- `stop_all_sound` (0x516C) confirmed = stop-all-sound.

## Resolved (sprint 0064) — byte-exact track decode

The whole music-data region **0x5236–0x5A10 is 100 % accounted for** as known
tokens. `tools/decode_tracks.py` walks all 27 events / 51 voices with the exact
`advance_track_stream` grammar; union of consumed bytes + engine tables + tail
padding = the region with **0 gaps, 0 unknown opcodes**. See
[[sound_track_scores]] for per-event maps, the byte accounting (pointer table /
duration table / curve tables / 7 embedded IDX_TRANSPOSE tables / `FF FF`
padding), and the format edge cases. Command jump table confirmed at **0x4F6C**;
operand lengths: `0x80/81/83/8A/8B/8C` = 2, `0x84–0x89` = 1, `0x82 END` = 0.
Chains ev7→ev1 / ev12→ev5 found statically; ev3 title-music note stream
live-matched (`tools/verify_tracks_live.py`). **Note:** the region's true end is
0x5A10 — `0x5A11` (`CD`) is already code (`CALL 0x46BC`).

## Resolved (2026-07-30, found while porting) — note→period math

`init_psg_freq_table` (0x513F) lays the 0xF200 table out as
`entry(semitone, octave) = base[semitone] >> octave` at address
`0xF200 + semitone*2 + octave*0x19`:

```
5147  BC=0x51F0; CALL lookup_word_table   ; DE = base period for semitone B
5150  LD (HL),E / (HL+1),D                ; write one octave's word
5153  LD BC,0x17; ADD HL,BC               ; +2 (the write) +0x17 = stride 0x19
5157  SRL D / RR E                        ; halve -> next octave
515B  x10 octaves, then DE += 2 -> next semitone column
```

With the stream's `note = octave*12 + semitone + 1` (0 = rest):
**`period(note) = base[(note−1) mod 12] >> ((note−1) / 12)`**, base = the 12
words at [[psg_period_base_table]] (0x51F0). The old "stride 0x17" note was the
`ADD HL,0x17` seen in isolation — the effective row stride is 0x19 because the
two-byte write precedes it.

Verified in the web port: interpreting event 3 with exactly this mapping loads
3 voices on channels 0/1/2 with streams 0x5458/0x54DC/0x550A (matching
[[sound_track_scores]]) and yields octave-paired channel-A periods
(511/255 = 4092>>3 / >>4).

## Resolved (2026-07-30) — the two ramps

Both "fine details" items are now read; each is a **fractional accumulator**
that steps only when the 8-bit `rate + acc` addition carries (i.e. rate/256
steps per frame), and neither is linear in the way earlier notes assumed:

**Volume envelope (0x4ED3)** — fade-down only:

```
4ED3  acc(slot[15]) += rate(slot[14]); RET NC
4EDE  if amp(slot[1]) == target(slot[16]): SET play-flag bit1   ; done
4EEC  else RES bit1; DEC amp                                    ; always down
```

`amp` only ever decrements; play-flag bit 1 (the `JUMP_IF_ENV` condition) is
set when it reaches the 0x8B target. There is no fade-up path.

**Pitch slide (0x4F0D)** — geometric, not linear:

```
4F0D  acc(slot[11]) += rate(slot[10]); RET NC
4F17  shift = slot[17]; RET Z
4F1C  BC = period(slot[12/13]) >> shift; HL = period
4F2D  play-flag bit6 clear -> HL += BC; if H >= 0x10 -> HL = 0
      play-flag bit6 set   -> HL -= BC; if borrow    -> HL = 0
4F43  period = HL
```

Each step moves the period by `period >> shift`, so the glide is exponential
in frequency; overflow past 0x0FFF or underflow clamps the period to 0, which
silences the channel. 19 of the 27 events use 0x8B/0x8C in their streams, so
these ramps carry most of the SFX character (the shot sound ev13's descending
sweep is the 0x8C glide).

Verified in the web port (`web/src/psg.js`): ev22 fades 15→14→13→12 at one
step per five frames, matching its rate byte's carry cadence.

## Outstanding questions

(none at engine level — remaining fidelity items are content-level listening
comparisons against real hardware.)
