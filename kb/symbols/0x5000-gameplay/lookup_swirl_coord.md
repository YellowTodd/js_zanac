---
address: 0x5B91
end: 0x5B9F
kind: routine
name: lookup_swirl_coord
confidence: confirmed
inputs:
  A: swirl-path index (a logo row's countdown, 0–0x1B)
outputs:
  HL: "name-table coordinate from logo_swirl_path[A] (L=row, H=col)"
clobbers: [AF, DE, HL]
calls: []
called_by: [0x5A5E, 0x5A8E]
tags: [title-screen, animation]
sprint: "0042"
---

# lookup_swirl_coord

## Summary

Returns the `(row, col)` name-table coordinate for a logo row at swirl step `A`,
by reading the 2-byte entry `logo_swirl_path[A]` (table at 0x5B59). Used by the
title logo animation in `title_intro_seq`.

## Analysis (source 0x5B91–0x5B9F)

```
5B91  PUSH BC
5B92  ADD A,A            ; A *= 2 (word index)
5B93  LD BC,0x5B59       ; logo_swirl_path base
5B96  LD L,A; LD H,0     ; HL = 2*A
5B99  ADD HL,BC          ; HL → path[A]
5B9A  LD D,(HL); INC HL; LD E,(HL)
5B9D  EX DE,HL           ; HL = path entry (L=row, H=col)
5B9E  POP BC
5B9F  RET
```

The caller adds the logo row index (`0xE1F9`, 0–4) to `L` so the five rows stack
vertically at the home position, then passes `HL` to `draw_logo_row`.

## See also

`logo_swirl_path` (0x5B59 data), `draw_logo_row` (0x5BA0), `title_intro_seq`.
