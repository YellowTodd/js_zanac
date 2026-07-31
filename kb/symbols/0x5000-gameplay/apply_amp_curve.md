---
address: 0x5099
end: 0x50D1
kind: routine
name: apply_amp_curve
confidence: confirmed
inputs: { IX: "sound-engine slot base" }
outputs: { "slot[0x0E]": "per-tick output amplitude (0-15)" }
clobbers: [AF, BC, HL]
called_by: [0x4E7B]
tags: [audio, psg, sound-engine, envelope]
sprint: "0028"
---

# apply_amp_curve

## Summary

**Per-tick volume-curve (instrument envelope) modulator.** Called every frame
from `psg_sound_tick` (0x4EC0) for each active voice. Reads the voice's
volume-curve shape (selected by slot[0x02], set by track command `SET_CURVE`
0x84) at the current phase index slot[0x1A], and computes the attenuated
**output amplitude** into slot[0x0E], which `output_slot_to_psg` (0x50D2) then
writes to the PSG volume register.

The sprint-0020 hypothesis that 0x5099 was the "note sequencer" was **wrong** —
note fetching is `advance_track_stream` (0x4F4A). 0x5099 only shapes amplitude.

## Analysis

```
5099  LD A,(IX+2); ADD A,A          ; A = 2 * curve selector
509D  JP Z, 0x50CC                  ; selector 0 -> flat (no curve)
50A0  LD HL,0x527D; ...; ADD HL,BC  ; HL = curve pointer table[selector]
50A7  LD C,(HL); INC HL; LD B,(HL)  ; BC = curve data address
50AA  LD L,(IX+0x1A); INC (IX+0x1A) ; phase index, then advance
50B2  ADD HL,BC; LD A,(HL)          ; A = curve[phase]
50B4  BIT 7,A; JR Z,0x50BD          ; 0x80 = sustain marker:
50B8  DEC HL; DEC (IX+0x1A); LD A,(HL)  ;   hold at last value (don't advance)
50BD  CPL; ADD A,0x10; LD B,A       ; B = 0x0F - curve_value   (attenuation)
50C1  LD A,(IX+1); SUB B            ; output = base_amp - (15 - curve_value)
50C5  JR NC,0x50C8; SUB A           ; clamp to 0
50C8  LD (IX+0x0E),A; RET           ; store output amplitude
50CC  LD A,(IX+1); JP 0x50C8        ; flat: output = base amplitude
```

A curve byte of 0x0F = full level (output = base amplitude slot[0x01]); lower
values attenuate. The 0x80 byte is a **sustain/loop marker**: the phase backs
up one entry and re-reads, holding the final pre-0x80 level for the rest of the
note.

## Volume-curve tables

`slot[0x02]` indexes the word pointer table at **0x527D**:

| Sel | Addr   | Shape (levels until 0x80 sustain) |
|-----|--------|-----------------------------------|
| 0   | 0x241C | flat / unused (points outside the sound area) |
| 1   | 0x528D | `0F 0E 0D 0C 0B 0A 09` — linear decay |
| 2   | 0x5295 | `0F 0D 0A 07 04 02 00` — fast decay to silence |
| 3   | 0x529D | `0D 0E 0F 0E 0C 0A 08` — soft attack then decay |
| 4   | 0x52A5 | `0F×6 0E 0C 0A 08 00` — sustain then decay |
| 5   | 0x52B2 | `07 09 0C 0F …` slow staircase decay |
| 6   | 0x52CC | `08 0D 0F×8 0E` — sustained |
| 7   | 0x52D8 | `0D 0F 0F 0E 0D 0C 0B 0A 09` — decay |

These are the engine's "instruments": the title music assigns curve 7 to ch A,
2 to ch B, 1 to ch C.
