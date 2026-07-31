---
address: 0x5BFC
kind: routine
name: vdp_write_byte_di
confidence: confirmed
sprint: "0043"
tags: [video]
---

# vdp_write_byte_di

## Summary
Write A directly to VDP data port (0x98) with interrupts disabled; faster than WRTVRM.

## Analysis
Source lines 1926–1933. DI / PUSH BC / LD BC,(0x0007) / OUT (C),A / POP BC / EI. Reads VDP I/O port from BIOS at ROM address 0x0007 (= 0x98 in standard MSX). Used to stream sequential bytes after SETWRT without the BIOS overhead of WRTVRM.

## Live confirmation (sprint 0043)
Micro-exec: SETWRT(vaddr) via 0x0053, then 0x5BFC with A=value, then read VRAM
back. `0x3A00←0x5A`, `0x3A01←0xC3`, `0x3A40←0x7E` all landed correctly in VRAM,
confirming the single-byte autoincrement write. `tools/sprint0043_verify.py`.
