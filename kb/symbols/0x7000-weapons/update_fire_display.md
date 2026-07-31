---
address: 0x7594
end: 0x75d4
kind: routine
name: update_fire_display
confidence: confirmed
inputs:  { "(E14B)": "fire_num", "(E14D)": "ammo/counter" }
outputs: {}
clobbers: [AF, BC, DE, HL]
calls: [0x42ed, BIOS:SETWRT, 0x5c1f, 0x5bfc, 0x4b8d, 0x42f8]
called_by: [0x7312, 0x732e, 0x74d0, 0x7591]
sprint: "0048"
tags: [fire, weapon, hud, vram, display]
---

# update_fire_display

## Summary

Draws the **FIRE readout** in the status area: the `"FIRE "` label + the current
`fire_num` digit at VRAM 0x3a59, and the ammo/durability counter (E14D, 3-digit)
at 0x3a7a. This is the routine the HUD subsystem ([[N-hud-and-status-display]])
noted as "rendered by the fire-weapon handler using N's digit primitives" — it
belongs to F. The old sprint-0002 name `update_fire_display` at 0x4DA5 was a
mis-attribution (that address is the [[pause_handler]]); the real fire display is
here.

## Analysis (0x7594–0x75d4)

```
CALL 0x42ed                       ; vdp_int_disable
LD HL,0x3a59; CALL SETWRT
CALL 0x5c1f -> "FIRE ",0          ; inline string (label)
LD A,(E14B); ADD 0x30; CALL 0x5bfc ; fire_num digit -> 0x3a5e (vdp_write_byte_di)
LD HL,0x3a7a; CALL SETWRT
A,(E14B)==0 ? print blank : { A,(E14D); CALL 0x4b8d }  ; 3-digit ammo at 0x3a7a
JP 0x42f8                          ; vdp_int_enable -> RET
```

Uses N's digit primitive `0x4b8d` (3-digit, leading-zero blanked) and
`vdp_write_byte_di` (0x5bfc).

## Confirmed (sprint 0048)

Micro-exec with E14B=3, E14D=0x40: VRAM 0x3a59 = `"FIRE "`, 0x3a5e = `'3'`,
0x3a7a = `" 64"` (leading-zero blank). `tools/sprint0048_live.py`.
