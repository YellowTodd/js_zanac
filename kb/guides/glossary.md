# Glossary

Short definitions for terms that recur across symbol entries and sprint notes. Keep entries one or two sentences; link to external references rather than re-explaining hardware.

## MSX system

- **BIOS** — The MSX Main-ROM routines starting at `0x0000`. Standard entries (`CHPUT`, `WRTVRM`, `CALSLT`, etc.) are documented in the MSX Technical Data Book.
- **System variables** — RAM area starting at `0xF380` used by the BIOS and BASIC interpreter (e.g. `CLIKSW`, `HKEYI`).
- **HKEYI / HTIMI** — Interrupt hook vectors at `0xFD9A` and `0xFD9F`. Games typically patch these to install their own VBLANK handler.
- **Slot** — MSX memory paging unit. `RDSLT`/`WRSLT`/`CALSLT` BIOS routines switch slots for the duration of a memory access or call.
- **Page** — A 16 KB Z80 address-space quarter (`0x0000`, `0x4000`, `0x8000`, `0xC000`).

## Video (VDP / TMS9918)

- **VRAM** — 16 KB video memory, accessed through I/O ports `0x98` (data) and `0x99` (address/register).
- **Pattern table / Name table / Color table** — Screen-mode-dependent VDP tables. Zanac uses Screen 2 (Graphic II); see the relevant feature note.
- **Sprite attribute table (SAT)** — 32 × 4 bytes describing on-screen sprite positions, patterns, and colors. Zanac shadows this in RAM and copies to VRAM during VBLANK.
- **VBLANK** — Vertical blanking interrupt, ~60 Hz on NTSC. The only safe window for bulk VRAM updates.

## Sound (PSG / AY-3-8910)

- **PSG** — Programmable Sound Generator at I/O ports `0xA0` (register select), `0xA1` (data write), `0xA2` (data read).
- **PSG registers 0–13** — Tone period (low/high) for channels A/B/C, noise period, mixer, volume/envelope per channel, envelope period and shape.
- **Track / pattern / note** — Game-specific sound-engine vocabulary; defined in `kb/features/sound-engine.md` once that sprint runs.

## Z80 conventions

- **RST n** — One-byte calls to `0x00`, `0x08`, ... `0x38`. Often repurposed by games as compact dispatchers.
- **IM 1** — Interrupt mode 1; the Z80 jumps to `0x0038` on `INT`. MSX BIOS sits at this address and routes through `HKEYI`/`HTIMI`.
- **Shadow registers** — `AF'`, `BC'`, `DE'`, `HL'`. Commonly used by interrupt handlers to avoid saving state on the stack.

## Project terms

- **Sprint** — One scoped batch of analysis, recorded as `kb/sprints/NNNN-*.md`.
- **Shadow table** — A RAM copy of a VRAM structure, updated freely and bulk-copied during VBLANK.
- **Thunk** — A small wrapper routine that fixes up registers and forwards to a BIOS or library call.
