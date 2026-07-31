---
address: 0x9480
end: 0x94C2
kind: routine
name: scroll_velocity_ctrl
confidence: likely
inputs:  {}
outputs: {}
clobbers: [AF, IX]
calls:   []
called_by: []
tags: [scroll, timing]
sprint: "0010"
---

# scroll_velocity_ctrl

## Summary

Adjusts the current scroll speed (0xE710) toward the target speed (0xE712),
using a mod-4 timing counter (0xE713) to smooth the transition. Reads
`base_encounter_flags` (0xE150) to bypass velocity adjustment during an
active base encounter (bit 0 or 1 of 0xE150 set).

Also clears bit 1 of `scroll_flags` at the start of each call (0x948A).

## Analysis

Source lines 6137–6164 (approx.).

```
9480  LD A, (0xE102)         ; read player state byte
9483  BIT 5, A               ; test bit 5
9485  RET NZ                 ; return if set (game paused / player dead?)
9486  LD IX, 0xE700          ; IX = scroll_state base
948A  RES 1,(IX+0)           ; clear bit 1 of scroll_flags (frame start)
948E  LD A, (0xE150)         ; read base_encounter_flags
9491  AND 0x03               ; mask bits 0-1 — sets Z if no base active
9493  LD A, (IX+0x10)        ; A = current_scroll_speed (0xE710) — no flag change
9496  JR NZ, 0x94B5          ; if base active (Z=0 from AND), skip velocity adjust
9498  CP (IX+0x12)           ; compare with target_scroll_speed (0xE712)
949B  JR Z, 0x94B5           ; if equal, no adjustment needed
949D  PUSH AF                ; save current speed and carry (< or > target)
949E  INC (IX+0x13)          ; increment timing counter (0xE713)
94A1  LD A, (IX+0x13)
94A4  AND 0x03               ; only adjust every 4th call
94A6  JR Z, 0x94AB
94A8  POP AF
94A9  JR 0x94B5              ; not time yet, skip
94AB  POP AF
94AC  JR C, 0x94B1           ; if current < target → INC
94AE  DEC A                  ; current > target → decrement toward target
94AF  JR 0x94B2
94B1  INC A                  ; increment toward target
94B2  LD (IX+0x10), A        ; store updated current_scroll_speed
; ... continues: further adjustments and possibly scroll_sync call
```

## Notes

- 0xE710 = `current_scroll_speed` (stable at 0x34 during normal scrolling).
- 0xE712 = `target_scroll_speed` (0x34 = full speed; changes to 0 when
  approaching a base).
- 0xE713 = mod-4 timing divider (speed steps are taken every 4 frames).
- When 0xE150 & 0x03 ≠ 0 (base encounter active), the velocity adjustment
  is completely bypassed. A separate mechanism decelerates the scroll toward
  the base (not yet traced).
