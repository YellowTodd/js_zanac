---
address: 0x4C68
end: 0x4C73
kind: routine
name: render_round_digit
confidence: confirmed
inputs: {}
outputs: {}
clobbers: [AF, HL]
calls:   [0x42ED, 0x4B83]
called_by: [0x4C4D]
sprint: "0047"
tags: [hud, round, video]
---

# render_round_digit

## Summary
Render the current **round** number (`E701`) as a 2-digit decimal at VRAM
**0x3A1B** (the HUD "ROUND" readout).

> Correction (sprint 0047): previously named `render_hiscore_digit` and described
> as a hi-score digit. It reads `E701` (the round selector, see
> `round-progression`), not the hi-score, and feeds the 2-digit
> `write_digit_to_vram` entry.

## Analysis
Source 0x4C68: `CALL vdp_int_disable; LD A,(0xE701); LD HL,0x3A1B;
JP write_digit_to_vram` (0x4B83, 2-digit).

## Live confirmation (sprint 0047)
Micro-exec with E701=5 → VRAM 0x3A1B=" 5". Matches the in-game/credits HUD
"ROUND 0" readout (round 0 = ending) seen in sprint 0046. `tools/sprint0047_verify.py`.

## See also
- `update_status_bar.md` (0x4C4D) — the caller; also draws level + lives.
- `round-progression.md` — `E701` round semantics.
