---
address: 0x0007
kind: data
name: vdp_dw
confidence: confirmed
sprint: "0002"
tags: [bios, vdp]
---

# vdp_dw

## Summary
VDP data write port address (1 byte in ROM). Value = 0x98. Used by vdp_write_byte_di (0x5BFC): LD BC,(0x0007) / OUT (C),A. Writing port 0x98 stores A to VRAM at the current write address, then advances it.
