---
address: 0x5C10
end: 0x5C1E
kind: routine
name: vram_string_copy
confidence: confirmed
inputs:
  HL: pointer to a 0x00-terminated byte string
outputs:
  HL: advanced to just past the 0x00 terminator
clobbers: [AF]
calls: [0x5C07]
called_by: [0x5C20]
tags: [vram, text]
sprint: "0037"
---

# vram_string_copy

Copies a `0x00`-terminated byte string from `HL` to VRAM at the current VDP
write address (interrupts disabled during the transfer).

```
5C10  DI
5C11  LD  A,(HL)
5C12  AND A            ; 0x00 = terminator
5C13  INC HL           ; advance (before the zero test branch)
5C14  JP  NZ,5C19
5C17  EI
5C18  RET              ; HL now points just past the terminator
5C19  CALL vdp_write_byte  ; (0x5C07) emit A
5C1C  JP  5C11
```

Each non-zero byte is streamed via [[vdp_write_byte]] to the auto-incrementing
VDP write address. On return `HL` sits *after* the terminator, which is what
lets [[vram_print_inline]] resume caller execution past an inline string. Used
only through the inline trampoline (0x5C20 = [[vram_print_inline]]).
