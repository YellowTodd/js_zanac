---
address: 0x51F0
end: 0x5207
kind: data
name: psg_period_base_table
confidence: confirmed
sprint: "0065"
tags: [sound, psg, frequency, data-table, o-sound]
---

# psg_period_base_table (0x51F0–0x5207, 24 B)

## Summary

The **12-semitone base-period table** the sound engine expands into the runtime
PSG frequency table at 0xF200. 12 little-endian words (one chromatic octave):

```
0x0FFC 0x0F1C 0x0E40 0x0D74 0x0CB4 0x0BFC
0x0B50 0x0AAC 0x0A14 0x0984 0x08FC 0x0878
```

Descending (higher note = shorter PSG period); the ratio first→last
(0x0FFC / 0x0878 = 1.887 ≈ 2^(11/12)) spans exactly the 11 semitones of one
octave, confirming these are the 12 chromatic tone periods.

## Reader — `init_psg_freq_table` (0x513F)

```
0x513F  DE = 0xF200 ; B = 0
0x5147  BC = 0x51F0 ; CALL 0x51E6   ; SUB_ram_51e6: HL = *(0x51F0 + note*2)
0x514E  A = 0x0A                     ; 10 octaves
0x5150  fill 0xF200 stride, halving the period per octave
```

`SUB_ram_51E6` indexes this word table by note number; `init_psg_freq_table`
precomputes **12 notes × 10 octaves = 120 entries** at 0xF200 (period halved each
octave up). The sound sequencer reads 0xF200 to set channel frequency registers.

## Confidence

`confirmed` — the reader is quoted (0x5147) and the table directly seeds the
already-confirmed PSG frequency system ([[sound-engine]] §"PSG frequency table",
which already cited "base frequencies from ROM table at 0x51F0"). The values are
a deterministic chromatic period series. This is the concrete table behind that
reference; sprint 0064 accounts for the rest of the sound region.

## See also

[[sound-engine]], [[sound_track_scores]], `init_psg_freq_table` (0x513F).
