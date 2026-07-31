---
address: 0x4E45
kind: routine
name: map_page2
confidence: confirmed
end: 0x4E4F
calls:   [0x4E50, BIOS:ENASLT]
called_by: [0x4010]
sprint: "0040"
tags: [init, slot]
---

# map_page2

## Summary
Map the running cartridge's own slot into page 2 (0x8000–0xBFFF), making the
upper 16 KB of the game ROM (code + data at 0x8000+) accessible.

## Analysis (source 0x4E45–0x4E4F)
```
4E45  LD E,0x01
4E47  CALL 0x4E50        ; detect_slot — A = slot ID of the cartridge page
4E4A  LD HL,0x8000
4E4D  JP 0x0024          ; ENASLT(A=slot, HL=0x8000) — enable that slot at page 2
```
`detect_slot` resolves the slot the cartridge is actually running in (page 1),
and `ENASLT` mirrors it at page 2 so both ROM halves are paged in. Tail-call
(`JP ENASLT`) returns straight to `cold_start`. Called once, from `cold_start`.

> **BIOS-label note:** `0x0024` is **ENASLT**; the disassembler's comment is
> correct here, but several nearby BIOS calls in this area are mislabelled (see
> `init_vdp_regs`, `detect_slot`).

## Confidence

`confirmed` — live trace (sprint 0040): breaking at 0x4E4A (after `detect_slot`,
before ENASLT) on a fresh boot, `A = 0x01` / `E = 0x02` → ENASLT maps **slot 1**
into page 2. Confirmed page-2 ROM is readable afterward (`0x8094` returns valid
cart bytes), and the game executes page-2 code to reach gameplay.
