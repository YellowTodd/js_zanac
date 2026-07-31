---
address: 0x5199
end: 0x51E5
kind: routine
name: load_sound_event
confidence: confirmed
inputs: { A: "event index (1-27)" }
outputs: {}
clobbers: [AF, BC, DE, HL, IX]
calls:   [0x51E6]
called_by: [0x5189]
tags: [audio, psg, sound-engine, track-format]
sprint: "0028"
---

# load_sound_event

## Summary

Inner dispatcher of `play_sound_event` (0x5189). Looks up the event's track
data via the pointer table at **0x5234**, then walks the event's voice header
and copies each voice's init parameters into its sound-engine slot at 0xE20C,
arming it for playback.

## Analysis

```
5199  LD D,A; LD BC,0x5234; CALL 0x51E6  ; HL = *(0x5234 + 2*event) = track data
51A0  LD C,D                             ; C = event number (saved)
51A1  LD B,(HL); INC HL                  ; B = N = voice count
51A3  ; --- per voice ---
51A3  LD A,(HL); INC HL                  ; A = slot descriptor D
51A6  ...A = D*27...; LD HL,0xE20C; ADD HL,DE
51B5  PUSH HL; POP IX                    ; IX = 0xE20C + D*27  (target slot)
51BA  LD A,(HL); AND A; JR Z,0x51E0      ; voice's slot[0] byte == 0 -> skip voice
51BE  LD A,(DE); BIT 6,A; RET NZ         ; target slot busy (bit6) -> abort
51C2  LD (IX+0x18),C                     ; slot[0x18] = event number
51C6  LD BC,8; LDIR                      ; copy 8 header bytes -> slot[0..7]
51CC  SUB A; LD (IX+8/9/0x19),A          ; clear play-flags, seq counter, noise
51D6  INC A; LD (IX+0x0C),A; LD (IX+0x0A),A  ; tick=1, duration=1 (fetch on 1st tick)
51E0  ; (skip) LD (DE),A; INC HL
51E2  DEC B; JR NZ,0x51A3                ; next voice
```

## Track header / voice init format (confirmed)

```
Byte 0:                N = number of voices
For each voice (N):
  Byte 0:              slot descriptor D  -> slot = 0xE20C + D*27
  Bytes 1-8:           copied to slot[0..7]:
    slot[0] = voice-config flags (bit0=tone out, bit1=noise mode, bit6=busy)
    slot[1] = base amplitude (0-15)
    slot[2] = volume-curve selector (table 0x527D, see apply_amp_curve)
    slot[3] = transpose (semitones)
    slot[4] = tempo (frames per sub-step)
    slot[5] = PSG channel (0=A, 1=B, 2=C)
    slot[6..7] = track stream start pointer
```

If a voice's slot[0] byte is 0 the voice is skipped (its slot is cleared); a
nonzero value with bit 6 already set means the slot is busy and the whole event
is aborted (`RET NZ`).

## Verification

Confirmed live (sprint 0028): after title music (event 3) starts, the three
slots 0xE242/0xE25D/0xE278 contained exactly the header params decoded
statically — e.g. ch A `{cfg=0x41, amp=0x0F, curve=0x07, tempo=0x02, chan=0,
ptr=0x5458}`. See sprint 0028 summary.

## Event pointer table (0x5234)

27 events (index 1-27); index 0 is a sentinel. Each entry is a 16-bit ROM
address of track data. See `kb/guides/sound-engine.md`.
