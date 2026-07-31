---
address: 0x5BDD
kind: routine
name: tile_to_vram_addr
confidence: confirmed
sprint: "0043"
tags: [video]
---

# tile_to_vram_addr

## Summary
Convert (column, row) tile coordinates to Screen Mode 2 name-table VRAM address.
Inputs: `H` = column, `L` = row. Output: `HL` = `0x3800 + row*32 + col`.

## Analysis
Source lines 1903–1915. E=H (column save), H=0, D=0. HL shifted left 5× (×32). ADD HL, DE (+ column). ADD HL, 0x3800. Crystal-clear arithmetic. The name table in Screen 2 starts at 0x3800.

## Live confirmation (sprint 0043)
Micro-exec unit tests (H=col, L=row → HL):
`(0,0)→0x3800`, `(5,3)→0x3865`, `(31,23)→0x3AFF`, `(10,10)→0x394A` — all match
`0x3800 + row*32 + col`. `tools/sprint0043_verify.py`.
