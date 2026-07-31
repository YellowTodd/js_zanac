---
address: 0x5208
end: 0x520D
kind: routine
name: mute_sound
confidence: confirmed
inputs: {}
outputs: { "0xE200": "= 3 (fire-pending + paused bits set)" }
clobbers: [AF]
tags: [audio, psg, sound-engine]
sprint: "0028"
---

# mute_sound

## Summary

Silences the sound engine by writing `3` to the engine-flags byte 0xE200,
setting bit 0 (fire-sound-pending → next frame mutes all PSG channels) and
bit 1 (paused → `psg_sound_tick` returns early without running the sequencer).
Shares its tail with `restore_sound` (0x520E).

## Analysis

```
5208  LD A,0x03            ; bit0 = fire-pending, bit1 = paused
520A  LD (0xE200),A
520D  RET
```

Counterpart: `restore_sound` (0x520E) clears 0xE200 to re-enable playback.
