---
address: 0xF3E7
kind: data
name: statfl
confidence: confirmed
sprint: "0002"
tags: [sysvar, vdp, interrupt]
---

# statfl

## Summary
Mirror of VDP status register S#0. Bit 7 = INT (set each VBLANK, cleared on read). Bit 6 = 5S (fifth sprite detected). Bit 5 = C (sprite collision). Bits 4-0 = FS (number of first illegal sprite). Updated by the BIOS keyboard interrupt handler after reading port 0x99.
