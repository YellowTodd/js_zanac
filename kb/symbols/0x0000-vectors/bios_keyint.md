---
address: 0x0038
kind: routine
name: bios_keyint
confidence: confirmed
sprint: "0001"
tags: [bios, interrupt]
---

# bios_keyint

## Summary
MSX BIOS interrupt entry point (IM 1 vector). Routes through the
`HKEYI` and `HTIMI` hook vectors at `0xFD9A` and `0xFD9F`. Games install
their own VBLANK code by patching those hooks rather than this address.
