---
address: 0x5AC8
end: 0x5AF7
kind: routine
name: draw_title_text
confidence: confirmed
inputs: {}
outputs: {}
clobbers: [AF, BC, DE, HL]
calls: [0x5C25, 0x5C28]
called_by: [0x5A76]
tags: [title-screen, text, name-table]
sprint: "0042"
---

# draw_title_text

## Summary

Draws the title-screen **credit text lines** into the name table using the
inline-string `vdp_set_addr_write` helper (0x5C25 / 0x5C28): "GAME DESIGNED BY
COMPILE" at VRAM 0x39E3, then "PRODUCED BY…" and the further credit/copyright
lines. Called once per pass of the logo-swirl loop in `title_intro_seq` so the
text stays drawn while the logo flies in.

> Corrects the old `title_intro_seq.md` note that called `sub_5AC8` a
> "frame sync / wait VBlank" — it draws text, not timing. The per-pass frame
> wait is `wait_frames` (`sub_5BEC`, B=2) at 0x5AAB.

## Analysis (source 0x5AC8–0x5B58)

A chain of `LD HL,<name-table addr>; CALL vdp_set_addr_write; DB "<string>",0`
blocks, ending in `RET`. The bytes after each CALL are the literal string
(0x00-terminated); the helper consumes them and resumes past the terminator
(`EX (SP),HL` trick). The lines are now correctly represented as instructions +
`DB` strings in the asm (the inline strings used to be mis-decoded as code).

| VRAM | row,col | text |
|------|---------|------|
| 0x39E3 | 15,3 | `GAME DESIGNED BY COMPILE` |
| 0x3A03 | 16,3 | `PRODUCED      BY AII` |
| 0x3A23 | 17,3 | `PRESENTED     BY PONY INC.` |
| 0x3A43 | 18,3 | `COPYRIGHT @ 1986 PONY INC.` |
| 0x3A8E | — | tiles `E7 E9 EB` (decoration) |
| 0x3AAE | — | tiles `E8 EA EC` (decoration) |

(`@` = 0x40, the © glyph. Zanac MSX was developed by Compile, published by Pony
Inc. / Pony Canyon, 1986 — matching these lines.)

## See also

`vdp_set_addr_write` (0x5C25, with alt entry 0x5C28), `title_intro_seq`.
