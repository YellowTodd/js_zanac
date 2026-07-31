---
address: 0x8709
end: 0x8749
kind: routine
name: handler_type62_invisible_riser
confidence: confirmed
inputs:  { IX: "entity slot" }
outputs: {}
clobbers: [AF, BC, DE, HL]
calls:   [0x4898, 0x44ba]
called_by: [0x445f]
tags: [entity, enemy, trigger]
sprint: "0051"
---

# handler_type62_invisible_riser

**Type 62** — invisible upward-moving trigger. Pattern 0x00 (no sprite), moves up
(vy=-1), and uses its +0x0d frame counter to fire periodic events every 16
frames. A non-visual timed spawner/trigger rather than a drawn enemy.

```
8709  BIT 7,(IX+0x00) / JR NZ,0x8728
870f  LD (IX+0x09),0xff / LD (IX+0x08),0x80  ; vy ≈ -0.5 (rising)
8717  LD (IX+0x03),0x00                        ; invisible (pattern 0)
871b  LD (IX+0x04),0x87 / LD (IX+0x0c),0x01     ; colour, bflags Y-motion
8723  SET 7,(IX+0x00) / RET
; active (0x8728):
8728  LD A,(IX+0x0d) / INC (IX+0x0d) / LD B,A / AND 0x0f / JR NZ,0x874a  ; every 16 frames → event
```

## Related

[[entity_jump_table]] (62).
