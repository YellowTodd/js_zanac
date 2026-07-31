---
address: 0x513F
end: 0x516B
kind: routine
name: init_psg_freq_table
confidence: confirmed
inputs: {}
outputs: {}
clobbers: [AF, BC, DE, HL]
calls:   [0x51E6]
called_by: [0x4010]
tags: [audio, psg, init]
sprint: "0019"
---

# init_psg_freq_table

## Summary
Builds the PSG note-frequency lookup table in RAM at 0xF200. Precomputes
10 octave values for each of the 12 chromatic notes using base frequencies
from a ROM table at 0x51F0.

## Analysis
Source lines 1778–1808.

Outer loop: 12 iterations (B = 0 to 11 = notes C through B).
- Calls `sub_51E6` with BC=0x51F0, A=B to read the note's base frequency
  word from ROM: `HL = 0x51F0[B * 2]`.
- Inner loop (A = 10, counting down): writes 16-bit word (E, D) to RAM, then
  `SRL D / RR E` halves the value (right shift = one octave up / frequency up).
  Each slot in RAM is at stride 0x19 bytes (2-byte value + 0x17 pad = 0x19).

Result: 12 notes × 10 octaves = 120 entries, each 2 bytes, stride 0x19.
Base address 0xF200. The sound engine reads these at playback time to compute
PSG channel-A/B/C period registers.

**ROM frequency table at 0x51F0** (12 entries × 2 bytes):

| Note | Period (hex) |
|------|-------------|
| C0   | 0x0FFC       |
| C#0  | 0x0F1C       |
| D0   | 0x0E40       |
| D#0  | 0x0D74       |
| E0   | 0x0CB4       |
| F0   | 0x0BFC       |
| F#0  | 0x0B50       |
| G0   | 0x0AAC       |
| G#0  | 0x0A14       |
| A0   | 0x0984       |
| A#0  | 0x08FC       |
| B0   | 0x0878       |

Called once during cold boot before RAM is cleared (it runs before the LDIR
wipe at 0xE000, so the table it writes to (0xF200) is in the upper RAM area
preserved across the wipe of 0xE000–0xE7FF).
