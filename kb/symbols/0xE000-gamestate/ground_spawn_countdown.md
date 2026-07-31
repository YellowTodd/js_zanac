---
address: 0xE124
kind: data
name: ground_spawn_countdown
confidence: confirmed
sprint: "0027"
tags: [spawn, gamestate]
---

# ground_spawn_countdown

Countdown timer that triggers immediate ground-structure spawns.

Code at 0x84BC–0x84C6:
```z80
LD  HL, 0xE124
DEC (HL)              ; decrement countdown
JR  NZ, 0x84C9       ; not yet
LD  (HL), 0x10        ; reload to 16
LD  A, 0x01
LD  (0xE125), A       ; set spawn_trigger → immediate type-44 spawn
```

- Initialized to 6 at game start (0x41F9: `LD (IX+0x24), 6`)
- After first zero-crossing: reloads to 0x10 = 16
- Each zero-crossing fires spawn_trigger (E125 bit 0)
