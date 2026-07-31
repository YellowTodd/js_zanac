---
address: 0x4000
end: 0x400F
kind: data
name: rom_header
confidence: confirmed
format: msx_rom_header
sprint: "0001"
tags: [rom, header, init]
---

# rom_header

## Summary
Standard MSX cartridge ROM header. The first two bytes are the magic
`"AB"` (`0x41 0x42`); the next four words point to `INIT`, `STATEMENT`,
`DEVICE`, and `TEXT` entry points respectively (zero if unused).

## Analysis
Layout (16 bytes total):

| Offset | Size | Name      | Meaning                              |
|-------:|-----:|-----------|---------------------------------------|
| +0     | 2    | magic     | Must be `AB` for the BIOS to map      |
| +2     | 2    | init      | Called once on cartridge insert       |
| +4     | 2    | statement | BASIC `CALL` handler (usually 0)      |
| +6     | 2    | device    | Disk/device handler (usually 0)       |
| +8     | 2    | text      | BASIC text pointer (usually 0)        |
| +10    | 6    | reserved  | Six zero bytes                        |

## INIT pointer at 0x4002
The `init` word at **0x4002** is a `DW 0x4010` — a *data* pointer in the
cartridge header, **not** a routine. The BIOS reads it on cartridge insert and
calls 0x4010 (`cold_start`), which sets up the stack and falls into the main
game via `LAB_4042` ([[main_game_loop]]). Do not disassemble 0x4002 as code.

## Verification
- Confirmed by inspecting the first 16 bytes of the ROM image.
- Magic `0x41 0x42` matches at file offsets 0 and 1.
