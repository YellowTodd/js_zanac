---
address: 0xF3E0
kind: data
name: rg1sav
confidence: confirmed
sprint: "0002"
tags: [sysvar, vdp]
---

# rg1sav

## Summary
Mirror of VDP control register 1 (4/16K RAM, BL (blank), GINT (interrupt enable), M1, M3, SI (sprite size), MAG). Used by vdp_int_disable (0x42ED) and vdp_int_enable (0x42F8) to read-modify-write GINT and BL bits without a full register table write.

## Verification
Sprint 0003 (openMSX live read): after cold_start initialises the display,
RG1SAV reads 0x82 (BL=0, GINT=0) while the actual VDP R1 = 0xC2 (BL=1).
The game's enable_display (0x42E2) and disable_display (0x42D7) read RG1SAV,
modify the bit, write to VDP, but **do not write back to RG1SAV**. The shadow
therefore drifts from the true VDP state whenever display is toggled.
Use the live VDP debug debuggable — not the shadow — for accurate R1 reads.
