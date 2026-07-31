---
address: 0xFCC1
end: 0xFCC4
kind: data
name: exptbl
confidence: confirmed
sprint: "0002"
tags: [sysvar, slot]
---

# exptbl

## Summary
Slot expansion table (4 bytes, one per primary slot 0–3). 0x80 = slot is expanded (has secondary slots), 0 = not expanded. Slot 0 byte also contains the main BIOS-ROM slot address. Used by detect_slot (0x4E50) to find the cartridge slot.
