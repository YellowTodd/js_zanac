---
address: 0x5189
end: 0x5198
kind: routine
name: play_sound_event
confidence: confirmed
inputs: { A: "event index (music track or SFX id)" }
outputs: {}
clobbers: [AF, BC, DE, HL, IX]
calls:   [0x5199]
called_by: [0x4042, 0x5A11, 0x8E1F]
tags: [audio, psg, sound-engine]
sprint: "0019"
---

# play_sound_event

## Summary
Entry point for the sound engine's event dispatcher. Queues a music track or
sound effect into one of the 5 sound-engine slots at 0xE20C.

## Analysis
Source lines 1824–1836.

```
PUSH BC, HL, DE, IX
DI
CALL 0x5199     ; inner: look up event in table at 0x5234, fill free slot
EI
POP IX, DE, HL, BC
RET
```

The wrapper saves/restores registers around the critical section (DI/EI). The
inner routine `sub_5199` (0x5199) does the actual dispatch:

1. Looks up ROM address of event data from the pointer table at **0x5234**
   (indexed as `0x5234[A * 2]`, a 16-bit little-endian word).
2. Scans the 5 slots at 0xE20C (stride 0x1B bytes each) for a free slot
   (bit 6 of slot[0] == 0).
3. Copies the event's header bytes into the slot and marks it active.

## Known call sites
| Caller | A value | Effect |
|--------|---------|--------|
| `title_intro_seq` (0x5A11) | 3 | Start title-screen music |
| `LAB_4042` (main init) | varies | Start gameplay music (track from 0xE701) |
| `handler_type80_base_damage` (0x8E1F) | 0x12 (18) | Explosion sound effect |

## Sound engine slots
The 5 slots at 0xE20C (5 × 0x1B bytes) hold per-channel playback state for
the PSG. Bit 6 of slot[0] = "slot busy". `stop_all_sound` (0x516C)
clears all 5 slots and reinitializes the PSG hardware.

**Note:** Full sound engine decode is sprint 0020. The exact mapping from event
index to PSG channel assignments and the format of music data at 0xA624/0xA63C
are pending.
