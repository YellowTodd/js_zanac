---
address: 0xE1F8
kind: data
name: frame_counter
confidence: confirmed
sprint: "0004"
tags: [timing, vblank]
---

# frame_counter

## Summary
1-byte VBLANK frame counter. Incremented once per frame by `vblank_isr`; read
and cleared by `wait_one_frame` and `wait_frames` to implement frame-accurate
delays.

## Analysis
Source lines 397–401 (wait_one_frame), 484–485 (vblank_isr), cross-referenced
with sprint 0002's `wait_frames` KB entry (0x5BEC).

Confirmed triple-citation:
- `vblank_isr` (0x43DA+0xB): `LD HL, 0xE1F8; INC (HL)` — increment.
- `wait_one_frame` (0x4306): `LD A, (0xE1F8); SUB 1; JR C, loop; SUB A; LD (0xE1F8), A` — poll and clear.
- `wait_frames` (0x5BEC): inner loop clears and polls same address.

Overflows at 255 (wraps to 0) if the main loop does not clear it. In practice
callers clear it immediately after reading, so it is effectively 0 or 1.
