---
address: 0xF380
end: 0xF384
kind: routine
name: rdprim
confidence: confirmed
sprint: "0002"
tags: [bios, slot]
---

# rdprim

## Summary
5-byte inline routine: reads a byte from a primary slot. Called by RDSLT (0x000C). Performs slot switching for a single read without inter-slot call overhead.
