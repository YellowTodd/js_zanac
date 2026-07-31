---
id: "0018"
status: done
range: 0x43DA-0x445E
strategy: live_debug
budget_turns: 20
---

# Sprint 0018 — VBlank ISR pipeline and sprite shadow buffer

## Goal

Close the rendering pipeline from entity-slot update to screen pixels by:
1. Verifying the VBlank ISR fires at 60 Hz (BP counter on 0x43DA).
2. Identifying and comparing the sprite shadow buffer.
3. Decoding `sub_4E7B` (0x4E7B) — the player fire-trigger called from the ISR.
4. Identifying what `0x4560` does.

## Inputs

- `kb/symbols/0x4000-init/vblank_isr.md` — decoded ISR sequence
- `kb/symbols/0x4000-init/sub_4e7b.md` — known: reads 0xE200 fire-pending flag
- `kb/data/entity_table.md` — sprite-count at 0xE11F; entity slots 0xE300+
- `live-debug.md` Q6 — sprite shadow buffer format (hypothesis corrected here)

## Summary (filled at end)

### 1. ISR fire rate: 59 Hz confirmed (NTSC)

BP counter at 0x43DA measured 59 fires/second. ✓

### 2. Sprite shadow is at 0xE000, NOT 0xE180

**0xE180 is NOT the sprite shadow.** It is game state that `sub_41CB`
clears (48 bytes zeroed at game restart/title). The live-debug Q6 hypothesis
was wrong.

The **real SAT shadow** is at **0xE000**. Confirmed by:
- `entity_dispatch` (0x445F) initialises: `LD HL, 0xE000; LD (0xE122), HL`
- Entity handlers write SAT entries through the pointer at 0xE122
- ISR DMA loop: `LD HL, 0xE000; OUTI × sprite_count_bytes` → VRAM 0x3B80
- Live comparison: 0xE000 vs VRAM 0x3B80 → **126/128 bytes match** (2-byte
  mismatch = race at frame boundary while sprite 3 position was updating)

**SAT entry format in 0xE000** (confirmed 4 bytes/entry = TMS9918A standard):
`Y_pos, SAT_NAME, colour, X_pos`

**0xE11F** = number of SAT bytes to DMA (= active_sprites × 4).
**0xE122** = write pointer into 0xE000 (advanced by entity handlers).
**0xE127** = sprite flicker counter (incremented when 5S flag set in S#0).

### 3. VDP timing delays in DMA loop

The OUTI loop at 0x4405 is padded with two dummy reads after each byte:
```
OUTI               ; write (HL++) → VDP port (~16 cycles)
LD A, (0x0000)     ; delay: 13 cycles (value discarded)
LD A, (DE)         ; delay: 7 cycles  (value discarded)
JR NZ, loop        ; 12 cycles
```
Total ~48 cycles/byte at 3.58 MHz ≈ 13.4 µs/byte. Required to satisfy the
TMS9918A minimum inter-write timing.

### 4. Sprite flicker via 5S flag

When S#0 bit 6 (5S = too many sprites on one line) is set:
- 0xE127 is incremented
- On even counts: standard DMA from 0xE000
- On odd counts: **offset DMA** — reads from `0xE000 + B*1 + 4 - 8` (shifts
  which sprite subset is rendered), implementing per-line sprite rotation/
  flicker to work around the TMS9918A 4-sprites-per-line limit.

### 5. Collision check at 0x4560

`0x4560` is the **software sprite collision check** called from `entity_post`
(0x44BA) for each active entity. It:
- Reads `IY+0x03` (SAT_NAME of the entity)
- Indexes a **hitbox size table at 0x45C9** via `SAT_NAME >> 1`
- Reads `IY+0x01` (entity Y position); returns immediately if Y ≥ 0xF0 (off-screen)
- Compares `Y + size` against `B` (player/target Y) to detect overlap

**Hitbox size table (0x45C9, 32 bytes, indexed by SAT_NAME >> 1):**

| SAT_NAME | Pattern | Size | Note |
|---|---|---|---|
| 0x00 | pat0 (power_chip) | 0 | no collision |
| 0x04 | pat1 (comet) | 3 | |
| 0x14 | pat5 (small_star) | 3 | |
| 0x18 | pat6 (light_bar) | 5 | |
| 0x1C | pat7 (lead) | 6 | largest hitbox |
| 0x1E | (lead+1) | 6 | |
| 0x20 | pat8 (med_circle) | 1 | |
| 0x24 | pat9 (large_circle) | 0 | no collision here |
| 0x28 | pat10 (shot_single) | 0 | player shot — no hitbox |
| 0x34 | pat13 (super_hard_bolt) | 2 | |
| 0x38 | pat14 (player_ship) | 4 | |

Patterns not in the table have size 0. The collision check uses software
Y-range comparison; it is separate from the TMS9918A hardware collision bit
(S#0 bit C), which the ISR reads but does not appear to use for gameplay.

### 6. sub_4E7B fully decoded

```
4E7B  LD HL, 0xE200
4E7E  BIT 0, (HL)          ; test fire-sound-pending flag
4E80  RES 0, (HL)           ; always clear it
4E82  JP NZ, 0x5182         ; if flag was set: play fire sound (PSG GICINI)
4E85  BIT 1, (HL)           ; test E200 bit 1
4E87  RET NZ                ; if set: return (another path active)
4E88  LD A, 0xB8
4E8A  LD (0xE208), A        ; initialize fire animation header
4E8D-4E94: zero 0xE209–0xE20B
4E97  LD IX, 0xE20C         ; player_projectile_table (5 slots × 27 bytes)
4E9B  LD B, 0x05            ; scan all 5 slots
```

**0xE200 bit 0** = fire-sound-pending (set by player input handler when fire
occurs; cleared here; triggers PSG call at 0x5182 for the fire sound effect).

**`player_projectile_table` (0xE20C, 5×27 bytes)**: live capture shows 3 active
slots immediately after game start (active byte = 0x41 or 0x43 for the fire
weapon 0 shots). This is the **fire weapon shot tracking system**, managed by
the ISR — a **parallel system to entity dispatch**. SHIFT-key shots use entity
dispatch (type 2); Z-key fire weapon shots use 0xE20C.

### 7. 0xE1F8 is a per-frame signal, not a cumulative counter

`sub_5bec` zeros 0xE1F8 before waiting; the ISR sets it to 1 via `INC (HL)`.
It is a "VBlank occurred this frame" flag, not an incrementing counter.
Delta of 0 in a 0.5s poll is correct behaviour.

### New / updated KB files

- `kb/data/entity_table.md` — note 0xE000 as SAT shadow, update 0xE180 mis-ID
- `kb/symbols/0x4000-init/vblank_isr.md` — confirm shadow at 0xE000, add DMA
  timing detail, add 0xE127 flicker counter
- `kb/symbols/0x4000-init/sub_4e7b.md` — mark `confirmed`; add 0xE200/0xE20C
  fire-sound mechanism; confirm player_projectile_table usage
- `kb/data/player_projectile_table.md` — update: confirmed as fire-weapon shot
  tracking (Z key), parallel to entity dispatch

### Still uncertain

- The exact 27-byte slot layout of `player_projectile_table` (0xE20C)
- How `sub_5199` (0x5199, called from 0x5189) allocates a slot in 0xE20C
- The `0xE208–0xE20B` header bytes: likely fire-animation state machine

### Next sprint candidates

Already planned: 0019 (title screen), 0020 (sound engine), 0021 (entity slot).
An additional candidate: **0018b — player_projectile_table decode** — trace
0x5189/0x5199 to map the 27-byte fire-weapon slot layout.
