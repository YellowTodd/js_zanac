---
address: 0xE10C
kind: data
name: player_x_vel
confidence: confirmed
sprint: "0027"
tags: [player, gamestate, input]
---

# player_x_vel

Player X velocity byte computed each frame at the end of `sub_4343` (0x43BA:
`LD (0xE10C), A`). Derived from direction-key bits in input_state (0xE100):

- Base value: 4
- +3 for RIGHT, −3 for LEFT
- +1 for UP, −1 for DOWN

Range observed: 0x01–0x07 during normal play. Zero is possible but unusual.
