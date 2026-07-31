---
address: 0x730b
end: 0x7320
kind: routine
name: fire_life_timer
confidence: confirmed
inputs:  { "(E14C)": "frame counter", "(E14D)": "ammo/durability" }
outputs: {}
clobbers: [AF, HL]
calls: [0x7594]
called_by: [0x728f, 0x7306, 0x73c2]
sprint: "0048"
tags: [fire, weapon, timer, ammo]
---

# fire_life_timer

## Summary

Per-frame countdown for the active fire weapon. Decrements **E14C** every frame;
once every 0x3c (60) frames it refreshes the FIRE readout
([[update_fire_display]]) and decrements the ammo/durability counter **E14D**.
When E14D underflows (0x00 → 0xff), it pops its caller's return address and jumps
to [[fire_reset]] (0x7544) — i.e. the weapon expires and reverts to type 0.

## Analysis (0x730b–0x7320)

```
LD HL,0xe14c; DEC (HL); RET NZ        ; not a 60-frame boundary
LD (HL),0x3c; CALL 0x7594             ; reload, redraw FIRE readout
LD HL,0xe14d; DEC (HL); LD A,(HL)
CP 0xff; RET NZ                       ; ammo left
POP HL; JP 0x7544                     ; ammo gone -> fire_reset
```

Called from the fire-weapon handlers (0x728f, 0x7306, 0x73c2). The `POP HL`
discards the handler's return so expiry unwinds cleanly to `fire_reset`.

> Closes the 0x730b open question from **sprint 0038** (was hypothesised as a
> "fire_type branch"; it is the life/ammo timer).

## Confirmed (sprint 0048)

Reached via the confirmed fire-dispatch path; the E14C/E14D counter writes and
the 0x7594 redraw are confirmed by the engine + display tests.
`tools/sprint0048_verify.py`.
