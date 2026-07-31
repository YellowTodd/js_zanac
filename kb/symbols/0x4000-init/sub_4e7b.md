---
address: 0x4E7B
end: 0x4F00
kind: routine
name: psg_sound_tick
confidence: confirmed
calls:   [0x5182, 0x5099, 0x50D2, 0x4F4A, 0x0093]
called_by: [0x43DA]
tags: [audio, psg, sound-engine, isr]
sprint: "0020"
---

# psg_sound_tick

## Summary

**Per-frame PSG sound engine tick.** Called from `vblank_isr` every frame
(~59 Hz). Three responsibilities:
1. **Fire-sound fast path**: if 0xE200 bit 0 is set (Z-key pressed), mute
   all PSG channels immediately via GICINI (0x5182) and return — no sequencer
   update this frame.
2. **Sequencer**: initialise shadow PSG registers 7-10, then advance all 5
   sound-engine slots at 0xE20C (tick counters, note pointers, amplitude
   envelopes).
3. **PSG flush**: write shadow registers 0–10 (0xE201–0xE20B) to PSG hardware
   via 11 sequential GICINI calls.

## Analysis

```
4E7B  LD HL, 0xE200
4E7E  BIT 0, (HL)            ; test fire-sound-pending
4E80  RES 0, (HL)             ; always clear bit 0
4E82  JP NZ, 0x5182           ; fast path: mute PSG → GICINI(7, 0xBF)
4E85  BIT 1, (HL)             ; sound-engine-pause flag
4E87  RET NZ                  ; paused: skip sequencer entirely
4E88  LD A, 0xB8
4E8A  LD (0xE208), A          ; shadow R7  (mixer) = 0xB8 = tone A-C enabled
4E8D  SUB A; LD (0xE209), A   ; shadow R8  (ch A vol) = 0
4E91  LD (0xE20A), A          ; shadow R9  (ch B vol) = 0
4E94  LD (0xE20B), A          ; shadow R10 (ch C vol) = 0
4E97  LD IX, 0xE20C           ; sound-slot table base
4E9B  LD B, 5                 ; iterate 5 slots

; ---- Per-slot loop (4E9D) ----
4E9D  LD A, (IX+0)            ; A = slot active/type
      LD E, (IX+8)            ; E = play-flags byte
      AND A
      JP Z, 4EF1              ; skip inactive slots
      EXX
      DEC (IX+0x0C)           ; tick counter--
      JR NZ, 4EC0             ; not yet: jump to amplitude/freq update
      ; tick fired: reload counter from slot[4], advance sequence
      CALL 0x5099             ; advance note sequencer → updates E201-E207
      CALL 0x50D2             ; update amplitude → updates E209-E20B
4EF1  LD (IX+8), E            ; write back play-flags
      LD DE, 0x1B
      ADD IX, DE              ; next slot (stride 27)
      DEC B
      JP NZ, 4E9D             ; loop

; ---- PSG flush (4EF7) ----
4EF7  LD HL, 0xE201
      SUB A                   ; A = 0 (PSG register 0)
      LD E, (HL)              ; E = shadow value
      CALL 0x0093             ; GICINI(A, E) → write PSG reg A
      INC HL; INC A           ; next register
      CP 0x0B                 ; done after register 10?
      JP NZ, 4F01             ; loop for registers 0-10
      RET
```

## Shadow PSG register map (0xE200–0xE20B)

| Address | PSG Reg | Field |
|---------|---------|-------|
| 0xE200  | —       | engine flags (bit 0 = fire-sound-pending, bit 1 = paused) |
| 0xE201  | R0      | channel A frequency lo |
| 0xE202  | R1      | channel A frequency hi |
| 0xE203  | R2      | channel B frequency lo |
| 0xE204  | R3      | channel B frequency hi |
| 0xE205  | R4      | channel C frequency lo |
| 0xE206  | R5      | channel C frequency hi |
| 0xE207  | R6      | noise period |
| 0xE208  | R7      | mixer (init 0xB8 each frame) |
| 0xE209  | R8      | channel A volume |
| 0xE20A  | R9      | channel B volume |
| 0xE20B  | R10     | channel C volume |
| 0xE20C+ | —       | 5 × 27-byte sound-engine slots |

## Correction from sprint 0018

Sprint 0018 called 0xE20C the "player_projectile_table" for Z-key fire weapon
shots. **This was wrong.** 0xE20C holds **PSG sound-engine voice slots** filled
by `play_sound_event` (0x5189). The "3 active slots at game start" were the 3
PSG channels playing the title music (event 3), not fire-weapon projectiles.

The fire-weapon Z-key projectile system is a SEPARATE structure. Its exact
address is TBD — see sprint 0023.

## 0x5182 — PSG mute (fire-sound fast path)
```
5182  LD A, 7; LD E, 0xBF; JP GICINI
```
Resets PSG mixer register 7 to 0xBF (all channels off) via GICINI, then
returns to the ISR epilogue. Used as a one-frame "fire click" sound.
