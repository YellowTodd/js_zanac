---
address: 0x973E
end: 0x9741
kind: data
name: glyph_col_data
confidence: likely
sprint: "0063"
tags: [scroll, map-script, vdp, data-table]
---

# glyph_col_data  (asm label `glyph_col_data_973e`)

4-byte glyph column pattern (`00 00 70 50`) used by map-script **command 0xA**
(handler 0x96E5, [[level_script_format]]): the VRAM glyph blit merges this
4-column glyph with the command's fill nibble and writes it to VRAM 0x2538
via `LAB_970a`. Labelled in sprint 0056; this entry (0063) adds the KB extent
for the coverage audit. Byte-exact operand semantics of cmd 0xA are a sprint
0062 item.

## See also

[[level_script_format]] (cmd 0xA), `map_script_step` (0x94C3).
