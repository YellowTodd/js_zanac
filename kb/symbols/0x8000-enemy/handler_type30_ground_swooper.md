---
address: 0x7e9c
end: 0x7f72
kind: routine
name: handler_type30_ground_swooper
confidence: confirmed
inputs:  { IX: "entity slot" }
outputs: {}
clobbers: [AF, BC, DE, HL, IY]
calls:   [0x71da, 0x4898, 0x44ba]
called_by: [0x445f]
tags: [entity, enemy, swooper, paired]
sprint: "0050"
---

# handler_type30_ground_swooper

**Types 30 and 32** — a two-part swooper. Init spawns a **paired child** of type
`own+1` (30→31, 32→33 = stealth trackers, see [[handler_type31_stealth_tracker]]),
copying its own 13-byte header into the child. The two move together; the active
body aligns to the player and, once close, locks and reveals (sat 0xf4). Pattern
0xec (pat 59), colour flickers (XOR 0x06).

## Init (0x7e9c)

```
7e9c  BIT 7,(IX+0x00) / JP NZ,0x7f20        ; active → tracking body
7ea3  CALL 0x71da                             ; spawn_col_marker (HL = marker)
7ea6  LD (IX+0x0c),0x01 / +0x08=0x80 +0x09=0x01 ; bflags Y, vy ≈ 1.5
      +0x0a=0x80 +0x0b=0x01 +0x02=0x30          ; vx ≈ 1.5, X=48
      +0x03=0xec +0x04=0x8f / RES 6,(IX+0x05)
7eca  LD A,(IX+0x00) / CP 0x1e / JR Z,0x7ee1   ; type 30? keep down-motion
7ed1  SET 6,(IX+0x05) / +0x08=0 +0x09=0xff +0x01=0xd0  ; type 32: rise (vy=-1) from Y=208
7ee1  LD DE,0xfffd / ADD HL,DE / PUSH HL/POP IY ; IY = paired child slot (marker-3)
      EX DE,HL / PUSH IX/POP HL / LD BC,0x000d / LDIR  ; copy 13-byte header IX→child
7ef1  LD (IY+0x03),0xf0 / (IY+0x02)=0xc0 / (IY+0x0a)=0x80 / (IY+0x0b)=0xfe  ; child X=192 vx=-2
7f01  LD A,(IX+0x00) / INC A / LD (IY+0x00),A   ; child type = own + 1 (→ 31 / 33)
7f08  SET 7,(IX+0x00) / CP 0x1f / JP Z,0x7f73
7f11  LD (IX+0x0a),0 / (IY+0x0a)=0 / (IY+0x0b)=0xff / JP 0x7f73
```

## Active / tracking body (0x7f20)

```
7f20  BIT 7,(IX+0x05) / JR NZ,0x7f73         ; already locked → epilogue
7f26  (IY = +0x1b/1c child)
7f2f  A=(IX+0x00 & 0x7f)+1 / CP (IY+0x00) / JR NZ,0x7f81  ; child still alive?
7f3a  LD A,(0xe301) / CP (IX+0x01) / BIT 6,(IX+0x05) …     ; compare player Y
7f49  LD (IX+0x0c),0x02 / LD (IY+0x0c),0x02                 ; aligned → switch to X-motion
7f51  A=(IY+0x02)-(IX+0x02) / CP 0x0b / JR NC,0x7f73        ; pair within 11px?
7f5b  SET 7,(IX+0x05) / (IX+0x03)=0xf4 / (IY+0x00)=0x28     ; lock + reveal sprite 0xf4
7f67  (IX+0x02)+=5 / (IX+0x0c)=0x01
7f81  INC (IX+0x00)                                          ; child gone → advance own type
; epilogue (0x7f73 = LAB_ram_7f73):
7f73  LD A,(IX+0x04) / XOR 0x06 / LD (IX+0x04),A / CALL 0x4898 / JP 0x44ba
```

## Related

[[handler_type31_stealth_tracker]] (the paired child types 31/33),
[[spawn_col_marker]], [[entity_jump_table]] (30/32). The 0x7f73 epilogue is the
shared flicker+update tail also used by the stealth tracker.
