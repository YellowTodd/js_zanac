---
address: 0xE129
kind: data
name: player_y_snap
confidence: confirmed
sprint: "0027"
tags: [player, gamestate, position]
---

# player_y_snap / player_x_snap

Two adjacent bytes written by `player_pos_snapshot` at 0x4C8B:

```z80
LD  A, (0xE301)       ; entity slot 0, byte +0x01 = player Y
LD  (0xE129), A       ; player_y_snap
LD  A, (0xE302)       ; entity slot 0, byte +0x02 = player X
LD  (0xE12A), A       ; player_x_snap
```

After the snapshot the routine also writes to `0xE128` (entity_dir_flags):
computes relative direction bits (up/down/left/right/diagonal) from the delta
between this entity's position (IX+0x01, IX+0x02) and the player snapshot,
storing result in (IY+0x00) = 0xE128.

| Address | Name | Value (idle player) |
|---------|------|----------------------|
| 0xE129 | player_y_snap | 0xA0 = 160 (default Y center) |
| 0xE12A | player_x_snap | 0x78 = 120 (default X center) |
