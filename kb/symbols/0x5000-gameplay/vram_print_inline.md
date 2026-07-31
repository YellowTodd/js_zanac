---
address: 0x5C1F
end: 0x5C24
kind: routine
name: vram_print_inline
confidence: confirmed
inputs:
  "(SP)": return address points at a 0x00-terminated string immediately following the CALL
outputs: {}
clobbers: [AF]
calls: [0x5C10]
called_by: [0x5C2B, 0x759D, 0x75C0, 0x75C9]
tags: [vram, text]
sprint: "0037"
---

# vram_print_inline

Prints the `0x00`-terminated string that appears **inline right after the
`CALL 0x5C1F`**, to the current VDP write address, then resumes execution past
the string. Classic Z80 "print inline" trampoline.

```
5C1F  EX (SP),HL   ; HL = inline string ptr (old return addr); stack top = old HL
5C20  CALL vram_string_copy  ; (0x5C10) emit string; HL -> past terminator
5C23  EX (SP),HL   ; return addr = past-string ptr; restore old HL
5C24  RET
```

The VDP write address must already be set by the caller (via `SETWRT` or a
prior write). Direct callers ([[update_fire_display]] at 0x759D/0x75C0/0x75C9,
`vdp_set_addr_write`) set the address first, then embed the literal text. The
sibling entry [[vram_print_inline_hl]] (0x5C28, reaching here via 0x5C2B) sets
the address from `HL` first.
