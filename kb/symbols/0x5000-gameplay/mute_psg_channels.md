---
address: 0x5182
end: 0x5188
kind: routine
name: mute_psg_channels
confidence: confirmed
inputs: {}
outputs: {}
clobbers: [AF, E]
calls:   [BIOS:GICINI]
called_by: [0x4E7B]
tags: [audio, psg, sound-engine]
sprint: "0028"
---

# mute_psg_channels

## Summary

PSG fast-mute used by the fire-sound path. `psg_sound_tick` jumps here
(0x4E82) when 0xE200 bit 0 (fire-sound-pending) is set: it writes PSG mixer
register 7 = 0xBF (all tone + noise channels off) via GICINI and returns,
skipping the sequencer for that one frame. The brief silence + music resuming
next frame produces the shot "click".

## Analysis

```
5182  LD A,0x07; LD E,0xBF; JP 0x0093   ; GICINI(reg=7, val=0xBF) -> tail-call
```

`JP 0x0093` tail-calls GICINI, which returns directly to `psg_sound_tick`'s
caller (the VBlank ISR). See `kb/guides/sound-engine.md` § Fire-sound mechanism.
