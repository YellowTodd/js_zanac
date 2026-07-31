---
address: 0x8f25
end: 0x8f5d
kind: routine
name: wide_struct_init
confidence: confirmed
inputs:  { IX: "entity slot" }
outputs: { CF: "set if still initialising / not yet placed" }
clobbers: [AF, HL]
calls:   [0xbfab, 0x48d0]
called_by: [0x87ab, 0x8eb7]
tags: [entity, enemy, base, scroll-gate]
sprint: "0052"
---

# wide_struct_init

Scroll gate / Y-scroller shared by the wide structures
([[handler_type70_wide_structure]], [[handler_type84_wide_variant]]). Until the
base scroll flag (0xe700 bit 1) is set the segment is held; once set it walks the
segment's Y down by 8 per frame until it reaches the play area, then sets the
active bit. Uses a `POP HL` trick so the *uninitialised* path returns to the
caller's caller (skipping the rest of the handler that frame).

```
8f25  BIT 7,(IX+0x00) / JR NZ,0x8f45        ; already active → run branch
8f2b  POP HL                                  ; discard handler return → return to its caller
8f2c  LD A,(0xe700) / BIT 1,A / RET Z          ; scroll not ready → bail
8f32  (IX+0x01) += 8 / RET NC                   ; scroll Y down; not yet wrapped → wait
8f3b  SET 7,(IX+0x00) / (IX+0x01) += 0x10 / JP (HL)  ; placed → activate, resume handler
; active branch (0x8f45):
8f45  SCF / LD A,(0xe700) / BIT 1,A / RET Z      ; (CF set = "busy")
8f4c  (IX+0x01) += 8 / CP 0xd0 / RET C            ; off bottom?
8f57  POP AF / CALL 0xbfab / JP 0x48d0             ; scrolled off → dec encounter + clear
```

## Related

[[handler_type70_wide_structure]], [[handler_type84_wide_variant]],
`dec_encounter` (0xbfab), [[entity_jump_table]].
