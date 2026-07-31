---
address: 0x516C
end: 0x5181
kind: routine
name: stop_all_sound
confidence: confirmed
inputs: {}
outputs: {}
clobbers: [AF, B, DE, IX]
calls:   [0x5182]
called_by: [0x4042, 0x40E5, 0x4125, 0x412A, 0x41DE, 0x4676, 0x9170, 0x9180, 0x9201, 0x9385]
sprint: "0068"
tags: [psg, audio, silence]
---

# stop_all_sound

**aka** `reset_enemies_and_psg` (pre-0068 name — a misnomer, retired in
the naming-consistency pass; older sprint docs may still use it).

## Summary
**Silence all sound.** Clears the active/busy flag (slot[0]) of all 5
sound-engine voice slots at 0xE20C, then writes PSG mixer register R7 = 0xBF to
disable every tone and noise output.

> **Renamed in 0068.** The old label `reset_enemies_and_psg` was a legacy
> misnomer: this routine touches *only* the PSG / sound slots — it does **not**
> reset enemy state. Callers that also reset enemies (e.g. `load_bg_level`) do
> that separately.

## Analysis (source 0x516C–0x5181, confirmed)
```
516C  PUSH IX
516E  LD IX,0xE20C ; DE,0x1B(27) ; B,5 ; A=0
5178  LD (IX+0),A ; ADD IX,DE ; DJNZ 5178   ; clear slot[0] × 5 (stride 27)
5180  POP IX
    ; falls through into mute_psg_channels (0x5182):
5182  LD A,7 ; LD E,0xBF ; JP WRTPSG (0x0093) ; R7 mixer = 0xBF → all off
```

Clearing slot[0] stops each voice's sequencer next tick (the tick loop skips
inactive slots); it then **falls through into [[mute_psg_channels]]** (0x5182 =
`WRTPSG(7,0xBF)`), which immediately mutes the hardware mixer — the same PSG-mute
entry the fire-sound fast path reaches. Called
at level load (`load_bg_level` 0x412A) and round/boss transitions (0x9170,
0x9201) to cut music before the next track starts. Full slot decode in sprint
0020/0028; confidence upgraded to confirmed in 0057.
