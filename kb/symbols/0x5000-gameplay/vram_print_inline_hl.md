---
address: 0x5C28
end: 0x5C2D
kind: routine
name: vram_print_inline_hl
confidence: confirmed
inputs:
  HL: destination VRAM address
  "(SP)": return address points at a 0x00-terminated string immediately following the CALL
outputs: {}
clobbers: [AF, HL]
calls: [0x0053, 0x5C1F]
called_by: [0x4BC7, 0x4BDF, 0x4BF2, 0x4BFE, 0x4C08, 0x4C14, 0x4C20, 0x5A33, 0x5AEA, 0x5B05, 0x5B26, 0x5B47, 0x5B51]
tags: [vram, text]
sprint: "0037"
---

# vram_print_inline_hl

Prints the `0x00`-terminated string that appears **inline right after the
`CALL 0x5C28`** to the VRAM address in `HL`, then resumes execution past the
string.

```
5C28  CALL 0x0053    ; SETWRT — set VDP write address = HL
5C2B  JP   5C1F      ; -> vram_print_inline (emit the inline string)
```

`SETWRT` (BIOS 0x0053) programs the auto-incrementing VDP write pointer from
`HL`; [[vram_print_inline]] (0x5C1F) then streams the literal bytes via
[[vram_string_copy]] / [[vdp_write_byte]] and returns just past the terminator.

This is the interrupt-agnostic entry (assumes the caller already gated
interrupts). The sibling entry [[vdp_set_addr_write]] (0x5C25) runs a `0x42ED`
prefix first and falls in here. Engine-wide text-blit utility physically located
inside the decompressor block; direct callers are the title-screen text
(`draw_title_text` 0x4BC7–0x4C20, `title_intro_seq` 0x5A33+).
