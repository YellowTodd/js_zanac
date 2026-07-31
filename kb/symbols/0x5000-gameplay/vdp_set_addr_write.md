---
address: 0x5C25
end: 0x5C27
kind: routine
name: vdp_set_addr_write
confidence: confirmed
calls:   [0x42ED]
called_by: [0x468D, 0x5A27, 0x5AB7, 0x5ACB, 0x901D, 0x918C, 0x9318, 0x96BF, 0xBFD9]
sprint: "0037"
tags: [video, name-table, text]
---

# vdp_set_addr_write

## Summary

Coordinate-prefix entry to the inline-string VRAM printer. Calls `0x42ED`
(int-disable / cursor setup) and falls straight into [[vram_print_inline_hl]]
(0x5C28), which sets the VRAM write pointer and streams the null-terminated
string that follows the caller's `CALL` in the code stream. Used for the title
texts ("SCORE", "TOP", "GAME DESIGNED BY COMPILE", …) and the "ROUND n" banner
(0x96BF).

## Analysis (source 0x5C25–0x5C27, then falls into 0x5C28)

```
5C25  CALL 0x42ED        ; int-disable / cursor setup   ← main (coordinate) entry
5C28  ...                ; falls into vram_print_inline_hl (SETWRT + inline stream)
```

The two-entry structure lets callers choose whether the `0x42ED` prefix runs:
enter at **0x5C25** for the coordinate/int-disable path, or at **0x5C28**
([[vram_print_inline_hl]]) when interrupts are already gated (e.g. the "TOP"
write at 0x5A33). The actual byte streaming happens in [[vram_print_inline]]
(0x5C1F) via [[vram_string_copy]] (0x5C10) / [[vdp_write_byte]] (0x5C07).

## See also

`draw_title_text` (0x5AC8), `title_intro_seq`, [[vram_print_inline_hl]],
[[vdp_write_byte_di]] (0x5BFC).
