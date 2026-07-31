---
address: 0x520E
end: 0x5210
kind: routine
name: restore_sound
confidence: confirmed
inputs: {}
outputs: { "0xE200": "= 0 (clears fire-pending + paused)" }
clobbers: [AF]
tags: [audio, psg, sound-engine]
sprint: "0028"
---

# restore_sound

## Summary

Re-enables the sound engine by clearing the engine-flags byte 0xE200 to 0
(clears the paused and fire-pending bits), so `psg_sound_tick` resumes running
the sequencer each frame. Counterpart of `mute_sound` (0x5208); jumps into its
store tail.

## Analysis

```
520E  SUB A                ; A = 0
520F  JR 0x520A            ; -> LD (0xE200),A ; RET   (shared with mute_sound)
```
