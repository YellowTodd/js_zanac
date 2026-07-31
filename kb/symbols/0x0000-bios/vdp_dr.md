---
address: 0x0006
kind: data
name: vdp_dr
confidence: confirmed
sprint: "0002"
tags: [bios, vdp]
---

# vdp_dr

## Summary
VDP data read port address (1 byte in ROM). Value = 0x98. Reading port 0x98 returns the next byte from VRAM (via read-ahead buffer).
