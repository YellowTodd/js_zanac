---
address: 0x43DA
end: 0x43F7
kind: routine
name: vblank_isr
confidence: confirmed
calls:
  - 0x013E
  - 0x42ED
  - 0x0053
  - 0x4560
  - 0x9A79
  - 0x4E7B
sprint: "0018"
called_by: []
tags: [vblank, isr, sprite, timing]
---

# vblank_isr

## Summary

VBLANK interrupt service routine (0x43DA–0x445E). Installed at the H_TIMI hook
(RAM 0xFD9A–0xFD9C) by `cold_start` as `JP 0x43DA`. **Confirmed firing at 59 Hz**
(NTSC, sprint 0018 live count).

> Range note: the `end` frontmatter (0x43F7) marks only the ISR **prologue**
> (steps 1–6). The SAT-DMA body (0x43F8–0x4448) is the separate entry
> `sat_dma_to_vram`; the epilogue (0x444A–0x445E, steps 9–12) follows it. All
> three are described in sequence below.

## Decoded sequence

1. `POP AF` — discard BIOS H_TIMI return address; ISR owns the exit path.
2. `CALL 0x013E` (`JP 0x1770` in C-BIOS) — reads **VDP status register S#0**
   (port 0x99), acknowledging the interrupt and capturing sprite-collision/5S
   flags in A. `EX AF, AF'` stashes the result.
3. `CALL 0x42ED` (`vdp_int_disable`) — clears GINT (R1 bit 5) to prevent
   re-entrant VDP writes.
4. `LD HL, 0xE1F8; INC (HL)` — signal "VBlank occurred" to `sub_5bec`. Not a
   cumulative counter: `sub_5bec` zeros it before waiting and tests for non-zero.
5. `LD BC, (0x0007); LD HL, 0x3B80; CALL 0x0053` — set VDP write address to
   the SAT base at VRAM 0x3B80.
6. `LD A, (0xE11F); SUB 0` — load SAT DMA byte count; jump to terminator if 0.
7. **SAT DMA** (`0xE127` flicker path or normal) — see `sat_dma_to_vram.md`
   (0x43F8–0x4448) for the split-out detail:
   - `EX AF, AF'` — restore S#0 value (from step 2).
   - `BIT 6, A` — test **5S flag** (too many sprites on one line).
   - **Normal path** (5S clear): `LD HL, 0xE000; OUTI × E11F_bytes; JR NZ, loop`
     with two dummy reads between OUTIs as VDP timing delay (~48 cycles/byte).
   - **Flicker path** (5S set): increments `0xE127`; on odd counts, shifts the
     DMA source by ±8 bytes in 0xE000, rotating which sprite subset is rendered
     to work around the 4-sprites-per-line limit.
8. `LD A, 0xD0; OUT (C), A` — write SAT terminator (Y=208) to VDP.
9. `CALL 0x4560` — **software sprite collision check** (see below).
10. `CALL 0x9A79` (`scroll_vram_write`) — DMA prepared tile rows into VRAM
    name table for the vertical scroll.
11. `CALL 0x4E7B` — fire-sound trigger + player projectile tracking (see below).
12. Restore all registers and `RET`.

## SAT shadow at 0xE000

The sprite attribute table shadow lives at **0xE000** (NOT 0xE180).
- `entity_dispatch` (0x445F) initialises `(0xE122) = 0xE000` each frame.
- Entity handlers write 4-byte SAT entries (Y, SAT_NAME, colour, X) through
  the pointer at 0xE122, advancing it.
- **0xE11F** = byte count to DMA (active_sprites × 4).
- **0xE122** = current write pointer into 0xE000.
- **0xE127** = sprite flicker counter (incremented on 5S overflow).
- Live verification: 0xE000 vs VRAM 0x3B80 = 126/128 bytes matching; the 2
  non-matching bytes were a race on a moving sprite (sprint 0018).

**0xE180** is NOT the sprite shadow — it is game state zeroed by `sub_41CB`.

## 0x4560 — software collision check

Reads `IY+0x03` (SAT_NAME), indexes hitbox size table at 0x45C9 via
`SAT_NAME >> 1`, reads `IY+0x01` (Y), returns if Y ≥ 0xF0. Compares
`Y + size` against `B` to detect vertical overlap. Hardware sprite collision
(S#0 bit C) is read in step 2 but not used for gameplay collision logic.

**Hitbox size table at 0x45C9** (32 bytes, `SAT_NAME >> 1` → radius):

| SAT_NAME | Pattern | Radius |
|---|---|---|
| 0x04 | pat1 comet | 3 |
| 0x14 | pat5 small_star | 3 |
| 0x18 | pat6 light_bar | 5 |
| 0x1C–0x1E | pat7 lead | 6 |
| 0x20 | pat8 med_circle | 1 |
| 0x34 | pat13 super_hard_bolt | 2 |
| 0x38–0x3E | pat14–15 player_ship | 4 |
| all others | — | 0 (no collision) |

## 0x4E7B — fire-sound trigger and fire-weapon shot tracking

```
4E7E  BIT 0, (0xE200)    ; fire-sound-pending flag
4E80  RES 0, (0xE200)     ; always clear
4E82  JP NZ, 0x5182       ; play fire sound (PSG GICINI)
4E85  BIT 1, (0xE200)     ; some other flag
4E97  LD IX, 0xE20C; LD B, 5   ; advance the 5 PSG sound-engine slots
```

**0xE200 bit 0** = fire-sound-pending: set by player input handler when
the Z (fire weapon) key is pressed; cleared here and routed to the sound
driver at 0x5182.

**0xE20C** (5 × 27 bytes) = the **PSG sound-engine voice-slot table**, advanced
each frame by [[psg_sound_tick]] (0x4E7B). (Sprint 0018 mislabelled this the
"player_projectile_table" — the "active" bytes it saw, 0x41/0x43, are sound-voice
config bytes, bit6=busy/bit0=tone/bit1=noise; the 0x516C that clears it is
`stop_all_sound` = stop-all-sound. Corrected sprint 0067; the stale entry
was removed.) See [[sound-engine]] for the slot layout.
