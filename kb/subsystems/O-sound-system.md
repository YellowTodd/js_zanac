---
letter: O
title: Sound System
coverage: done
status: done
---

# O — Sound System

## Role

Music and sound effects on the AY-3-8910 PSG: the sound-event API (play/stop a
track or SFX), the per-frame voice tick that advances tracks and writes PSG
registers, amplitude/envelope shaping, and the channel mute/restore used around
events (e.g. the base-explosion silence). Driven from the ISR
([[B-frame-render-pipeline]]); invoked by [[J-title-screen]] (title music),
[[K-game-flow-state-machine]] (intro/main/game-over music), and
[[G-enemy-and-spawn-system]] / [[F-player-ship-and-weapons]] (SFX).

> Note: this subsystem was added after the initial A–M proposal (Sound had no
> letter assigned); it is user subsystem #2.

## Key routines

| Addr | Name | Conf | Notes |
|------|------|------|-------|
| 0x4E7B | `sub_4e7b` (psg_sound_tick) | confirmed | ISR PSG/fire-sound tick |
| 0x5099 | `apply_amp_curve` | confirmed | amplitude/envelope shaping |
| 0x50D2 | `output_slot_to_psg` | confirmed | write a voice slot to PSG regs |
| 0x513F | `init_psg_freq_table` | confirmed | build note→period table |
| 0x516C | `stop_all_sound` | confirmed | stop-all-sound (name is a misnomer — PSG only) |
| 0x5182 | `mute_psg_channels` | confirmed | mute channels |
| 0x5189 | `play_sound_event` | confirmed | start a track/SFX |
| 0x5199 | `load_sound_event` | confirmed | load event params |
| 0x5208 | `mute_sound` | confirmed | mute |
| 0x520E | `restore_sound` | confirmed | unmute/restore |
| 0x8BF5 | sound engine core (db) | confirmed | voice tick / note dispatch / vibrato / envelope (`LAB_ram_8ddb`, `8e1f`) |

## Data

- Event pointer table at **0x5234** (27 events); note-duration table at 0x526C;
  volume-curve table at 0x527D. Track data **0x52E2–0x5A11 (~2 KB)** — format
  decoded (0028) and **all 27 events catalogued** (structure + purpose +
  chaining, 0057). See `sound-engine` guide.
- **Event map** (live-confirmed 0057): round-start BGM = event 7 (or 2 on rounds
  ≡0 mod 8) → chains to event 1 (main theme); shot fire SFX = `3+(0xE10F>>2)`
  (0x7234, pitch by shot state); music/jingles = events 1–5, 7–12, 25–27;
  single-voice SFX = 6, 13–24; explosion = event 18; chaining `0x87 nn` (7→1, 12→5).

## Guides

- `sound-engine` (full command format + 27-event catalogue), `psg-ay-3-8910`.

## Status

**Done.** Engine (0020), track command format (0028), and full event catalogue
(0057) documented; `stop_all_sound` confirmed. Remaining items are
content-level (byte-exact "score" of each track) and two engine-internal fine
details (frequency-table index math, pitch-slide/vol-env), not undocumented
structure.

## Sprints

0020 (sound engine), 0028 (sound track format), 0057 (event catalogue — closing
slice).
