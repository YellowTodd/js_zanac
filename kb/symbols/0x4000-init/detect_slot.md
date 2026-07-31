---
address: 0x4E50
end: 0x4E7A
kind: routine
name: detect_slot
confidence: confirmed
calls:   [BIOS:RSLREG]
called_by: [0x4E45]
sprint: "0040"
tags: [init, slot]
---

# detect_slot

## Summary

Returns the full MSX slot ID of the page the running cartridge occupies, so
`map_page2` can mirror that slot into page 2. Standard hand-rolled slot search:
read the primary slot register, extract the 2-bit primary slot for the page,
then if that slot is expanded (per `EXPTBL`) read the secondary slot register and
fold in the 2-bit secondary slot.

## Analysis (source 0x4E50–0x4E7A)

```
4E50  INC E              ; E = page index used by the bit math
4E51  PUSH DE
4E52  CALL 0x0138        ; RSLREG — A = primary slot register (port A8h)
4E55  POP DE
4E56  RLCA; RLCA         ; rotate target page's 2 bits toward low nibble...
4E58  LD B,E
4E59  RRCA; RRCA; DJNZ   ; ...via E rotations
4E5D  AND 0x03           ; A = primary slot of the cartridge page
4E5F  LD C,A; LD B,0
4E62  LD HL,0xFCC1       ; EXPTBL (expanded-slot flags, 4 bytes)
4E65  ADD HL,BC
4E66  OR (HL); RET P     ; slot not expanded (bit7 clear) → return primary slot
4E68  LD C,A             ; expanded: keep primary in C
4E69  INC HL ×4          ; HL → SLTTBL entry (secondary slot reg shadow)
4E6D  LD A,(HL); RLCA; RLCA
4E70  DEC E; JR Z; RRCA; RRCA; JR  ; extract the page's secondary 2 bits
4E77  AND 0x0C           ; secondary slot bits
4E79  OR C               ; primary | (secondary<<2) | expanded flag
4E7A  RET
```

> **BIOS-label note:** `0x0138` is **RSLREG** (read primary slot register), not
> "sub_0138"; `0xFCC1` is the BIOS **EXPTBL** system variable. Verified against
> `kb/symbols/0x0000-bios/bios_rslreg.md` and `0xF380-sysvars/exptbl.md`.

## Output

`A` = encoded slot ID `Fxxx SSPP` (PP primary, SS secondary, bit7 = expanded),
the form expected by `ENASLT`. Called only by `map_page2` (0x4E45).

## Confidence

`confirmed` — live trace (sprint 0040). On the openMSX test machine the cartridge
slot is **not expanded**, so the routine takes the early `RET P` at 0x4E67 (the
0x4E7A RET is only reached for an expanded slot). Captured at `map_page2`'s
post-call site (0x4E4A): `A = 0x01` with `E = 0x02`, i.e. it resolved the
cartridge to **primary slot 1** for page 2.
