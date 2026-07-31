---
address: 0x42CF
end: 0x42D6
kind: data
name: vdp_init_table
confidence: confirmed
sprint: "0003"
tags: [vdp, init]
---

# vdp_init_table

## Summary
Eight-byte inline VDP register initialisation table at the end of `init_vdp_regs`
(0x42BA). Written to VDP registers 0–7 on every cold start.

## Analysis
Source line 367: `DB 0x02, 0x82, 0x0E, 0xFF, 0x03, 0x77, 0x03, 0x01`

Live verification via openMSX (sprint 0003): shadow registers RG0SAV–RG7SAV
at 0xF3DF exactly match this table immediately after the first call to
`vdp_int_enable` (0x42F8), confirming the table is written byte-for-byte.

| Offset | Register | Value | Meaning |
|--------|----------|-------|---------|
| +0 | R0 | 0x02 | M2=1 → Screen Mode 2 (Graphic II); EXTVID=0 |
| +1 | R1 | 0x82 | 4/16K=1, BL=0 (display off at init), GINT=0, SI=1 (16×16 sprites), MAG=0 |
| +2 | R2 | 0x0E | PN=14 → name table at 14×0x400 = **0x3800** |
| +3 | R3 | 0xFF | CT13=1 → color table at **0x2000**; AND mask=0x7F (all 3 CT banks) |
| +4 | R4 | 0x03 | PG13=0 → pattern table at **0x0000**; bank mask=0b11 (all 3 PG banks) |
| +5 | R5 | 0x77 | SA=0x77 → sprite attribute table at 0x77×0x80 = **0x3B80** |
| +6 | R6 | 0x03 | SG=3 → sprite generator table at 3×0x800 = **0x1800** |
| +7 | R7 | 0x01 | TC=0 (black text), BD=1 (black border/backdrop) |

## Verification
Sprint 0003: BP fired at 0x42F8; `debug read_block {VDP regs} 0 8` returned
`02 C2 0E FF 03 77 03 01` (R1=0xC2 because display was already enabled by then —
BL bit toggled by `enable_display` after init). Shadow at 0xF3DF confirmed 0x82
for R1 because the game's `enable_display`/`disable_display` do not write back
to the BIOS shadow RG1SAV.
