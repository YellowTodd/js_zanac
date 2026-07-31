---
address: 0x50D2
end: 0x5138
kind: routine
name: output_slot_to_psg
confidence: confirmed
inputs: { IX: "sound-engine slot base" }
outputs: { "0xE201-0xE20B": "shadow PSG freq/volume/mixer for this voice's channel" }
clobbers: [AF, BC, DE, HL]
called_by: [0x4E7B]
tags: [audio, psg, sound-engine]
sprint: "0028"
---

# output_slot_to_psg

## Summary

**Per-voice PSG output stage.** Called every frame from `psg_sound_tick`
(0x4ECA) after the note pointer and amplitude curve have been updated. Writes
the voice's current frequency (slot[0x12/0x13]), output amplitude (slot[0x0E])
and tone/noise mixer bits into the shadow PSG registers at 0xE201-0xE20B for
the voice's assigned channel (slot[0x05] = 0/1/2 → A/B/C). `psg_sound_tick`
later flushes the whole shadow block to hardware.

Sprint-0020 hypothesis "amplitude envelope" was imprecise — the envelope
*ramp* lives in `psg_sound_tick` (0x4ED3) and the curve in `apply_amp_curve`;
this routine is the channel mux/output.

## Analysis

```
50D2  LD A,(IX+0); LD B,A
50D6  BIT 5,B; JP Z,0x50EA        ; slot[0] bit5: re-init mixer/volumes first
50DB  LD A,0xB8;(E208)=A; SUB A;(E209/A/B)=0
50EA  LD E,(IX+0x12); LD D,(IX+0x13)   ; DE = target period
50F0  OR D; JR NZ; LD (IX+0x0E),A      ; period 0 (rest) -> force amp 0
50F7  BIT 0,B; JR NZ; LD DE,0          ; slot[0] bit0=0 -> silence freq
50FE  LD A,(IX+5); LD C,A              ; C = PSG channel (0/1/2)
5102  BIT 1,B                          ; slot[0] bit1 = noise mode?
5106  JR NZ,0x5116
5108  LD HL,0x513C; ADD HL,BC          ; tone-enable: OR mixer with mask
510F  ...; (E208)=A; JP 0x5127
5116  LD A,(IX+0x19);(E207)=A          ; noise mode: set noise period
511C  LD HL,0x5139; ADD HL,BC          ; noise-enable: AND mixer with mask
5127  LD HL,0xE209; ADD HL,BC          ; volume reg for channel
512B  LD A,(IX+0x0E); LD (HL),A        ; write output amplitude
512F  SLA C; LD HL,0xE201; ADD HL,BC   ; freq reg pair for channel
5135  LD (HL),E; INC HL; LD (HL),D     ; write period lo/hi
5138  RET
```

## Mixer mask tables

- **0x513C** (tone-enable OR masks, per channel): `08 10 …`
- **0x5139** (noise-enable AND masks, per channel): `F7 EF DF`
  (= ~0x08, ~0x10, ~0x20)

The shadow mixer (R7, 0xE208) starts at 0xB8 each frame (all tone on, noise
off); each voice ORs/ANDs in its own channel bits depending on tone vs noise
mode (slot[0] bit1).
