---
address: 0x4343
end: 0x43BF
kind: routine
name: read_player_input
confidence: confirmed
calls:   [0x42ED, BIOS:WRTPSG, BIOS:RDPSG, BIOS:SNSMAT, 0x42F8]
called_by: [0x46BC, 0x7612]
sprint: "0048"
tags: [input, player, joystick, keyboard]
---

# read_player_input

## Summary

Per-frame **player input poll** (formerly mis-named `read_options`). Reads both
joystick ports (via PSG R14/R15) and the keyboard direction/fire rows (via
SNSMAT), merges them into the active-low input byte at **0xE100**, then derives
the player's horizontal-movement selector into **0xE10C** (`player_x_vel`).
Called from the player-ship handler at 0x7612 — **not** from boot. Belongs to
[[F-player-ship-and-weapons]] (with [[K-game-flow-state-machine]] for the E100
input state); kept in `0x4000-init/` only because its address is in the 0x43xx
range.

## Analysis (source 0x4343–0x43BF)

```
4343  CALL 0x42ED               ; vdp_int_disable
      ; --- read both joystick ports via PSG I/O ports R14/R15 ---
4346  LD A,0x0F; LD E,0x8F; CALL 0x0093   ; WRTPSG(R15,0x8F) — select joystick port 1
434D  LD A,0x0E; CALL 0x0096               ; RDPSG(R14) → A = port-1 reading
4352  LD HL,0xE100; LD (HL),A             ; E100 = port-1 bits
4356  LD A,0x0F; LD E,0xCF; CALL 0x0093   ; WRTPSG(R15,0xCF) — select joystick port 2
435D  LD A,0x0E; CALL 0x0096               ; RDPSG(R14) → A = port-2 reading
4362  AND (HL); LD (HL),A                  ; E100 = port1 AND port2 (active-low merge)
      ; --- overlay keyboard rows via SNSMAT (0x0141) ---
4364  LD A,8; CALL SNSMAT   ; row 8 (cursor/space): RES bits 4,5 / 0 / 1 / 2 / 3 of E100 per key
4389  LD A,6; CALL SNSMAT   ; row 6: bit0 → RES 4
4394  LD A,5; CALL SNSMAT   ; row 5: bit7 → RES 5
      ; --- derive horizontal velocity selector from the 4 direction bits ---
439F  LD C,(HL); LD A,4     ; A starts at 4 = centered (no horizontal move)
43A2  BIT 0,C; if clear ADD A,1
43A8  BIT 1,C; if clear SUB 1
43AE  BIT 2,C; if clear SUB 3
43B4  BIT 3,C; if clear ADD 3
43BA  LD (0xE10C),A          ; player_x_vel selector (0..8; 4 = centre)
43BD  JP 0x42F8              ; vdp_int_enable
```

Callers: **0x7612** (player-ship handler) → `LD A,(0xE10C); CP 4` (centre? skip),
else index the X-velocity table at **0x7758** by E10C → apply ship horizontal
motion. **0x46BC** (`fire_edge_detect`) → polls input then edge-detects the fire
bits (E100 & 0x30) via E147.

> **BIOS-label note:** the disassembler mislabels the PSG calls. `0x0093` is
> **WRTPSG** and `0x0096` is **RDPSG** (the disasm says GICINI / WRTPSG); `0x0141`
> is **SNSMAT**. So steps 2–3 are a *two-port joystick read*, not "mute PSG
> channel A/B" as the old `read_options` note claimed. Verified against
> `kb/symbols/0x0000-bios/`.

## Corrections vs the old `read_options` entry

- Not a boot/title options reader — there is no options screen; it runs every
  gameplay frame from the player handler.
- The PSG writes select/read the **joystick ports**, they do not mute audio.
- `0xE100` is the active-low merged input byte (joystick ∧ keyboard), consistent
  with the E100 layout in `keyboard-input`.
- The value written to `0xE10C` is the **horizontal-velocity selector**
  (`player_x_vel`), not a difficulty value. (The earlier "difficulty → E10C"
  claim was the source of the A/I subsystem confusion.)

## See also

`keyboard-input` (E100 bit layout), `player_x_vel` (0xE10C), the X-velocity table
at 0x7758 ([[F-player-ship-and-weapons]]).
