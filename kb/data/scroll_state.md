---
address: 0xE700
end: 0xE721
kind: data
name: scroll_state
confidence: likely
sprint: "0010"
tags: [scroll, gamestate]
---

# scroll_state

## Summary

Scroll engine state variables occupying 0xE700–0xE71A (27 bytes). Shared between
the main-loop scroll pre-computation (`scroll_precompute` at 0x97E3,
`scroll_velocity_ctrl` at 0x9480), the VBLANK ISR callback
(`scroll_vram_write` at 0x9A79), and the sync routine (`scroll_sync` at 0x9AE4).

## Field layout

| Offset | Address | Name | Confidence | Notes |
|--------|---------|------|------------|-------|
| 0x00 | 0xE700 | scroll_flags | confirmed | Bit 0 = DMA-ready (SET by `scroll_precompute` at 0x9805; RES by ISR at 0x9A86). Bit 1 = secondary signal (SET at 0x9809; RES at 0x948A next frame). Bit 2 = alternate end-of-stream path (`BIT 2,(IX+0); JP NZ 0x980e` at 0x94C0 → logo reveal via `copy_tile_column`). Bit 3 = per-column VBLANK sync (`BIT 3,(IX+0); CALL NZ sub_9ae4` at 0x94C3). Both set (E700=0x0C) by `ending_setup` (`LAB_91fd`) for the credits logo-reveal phase; cleared by `LAB_92af`. |
| 0x01 | 0xE701 | stage_index | confirmed | Stage number set by `sub_9444` from the master script pointer table at 0x945C; selects the `& 7` / `& 3` index into tile-block tables 0xA444/0xA4A4/0xA564 (see `tile_tables.md`). **Correction from sprint 0008 which wrongly placed this at 0xE702.** |
| 0x02 | 0xE702 | level_row_ctr | confirmed | Absolute map-row counter; +1 per frame (`sub_94c3` at 0x94CA). Compared against `next_cmd_row` (0xE706) to trigger map-script commands. |
| 0x03 | 0xE703 | ? | guess | High byte of level_row_ctr (16-bit with 0xE702). |
| 0x04 | 0xE704 | stream_ptr | confirmed | 16-bit LE cursor into the level **map script** (e.g. 0xA7A0). Advanced by the command parser (`LAB_97d5` 0x97D5); points just past the last consumed command. See `kb/data/level_script_format.md`. |
| 0x06 | 0xE706 | next_cmd_row | confirmed | 16-bit LE row trigger of the next pending map command. When `level_row_ctr` (0xE702) reaches it, the command at `stream_ptr` is executed. Read from the 2-byte prefix of each map command. |
| 0x08 | 0xE708 | ? | guess | All zero during observed gameplay. |
| 0x0F | 0xE70F | ? | guess | Stable at 0x85 during normal scrolling; purpose unknown. |
| 0x10 | 0xE710 | current_scroll_speed | likely | Current scroll speed byte, adjusted toward `target_scroll_speed` by `scroll_velocity_ctrl`. Observed 0x34 during normal gameplay. |
| 0x11 | 0xE711 | scroll_timing_acc | hypothesis | Sub-frame timing accumulator; changes each frame (0x94→0x14 between two snapshots). Possibly fractional speed component. |
| 0x12 | 0xE712 | target_scroll_speed | likely | Target scroll speed; stable at 0x34 during normal scrolling. Compared against `current_scroll_speed` by `scroll_velocity_ctrl` at 0x9498. |
| 0x13 | 0xE713 | velocity_timer | likely | Mod-4 timing counter incremented by `scroll_velocity_ctrl` at 0x949E; speed steps taken only when (timer & 3) == 0. |
| 0x14 | 0xE714 | scroll_row | confirmed | Vertical row counter, 23→22→…→0→23 wrap. Decremented by `scroll_precompute`. |
| 0x15 | 0xE715 | tile_buf_ptr | confirmed | 16-bit LE pointer to the current row of the 24×24 ring at 0xE800; `= 0xE800 + scroll_row × 24`. Walks *down* by 24 per row (0x97ED) and wraps to 0xEA28. |
| 0x17 | 0xE717 | map_ptr | likely | 16-bit LE pointer advancing through the level tile-stream ROM data. (Also reused by the base handler at 0x8FDE as a rotating cursor over the 8-entry base-attack pattern table at 0x93AB.) |
| 0x1A | 0xE71A | row_build_cursor | confirmed | Write cursor into the **row assembly buffer at 0xEA40**, reset there on every call (0x98C8) and advanced as column groups and greeble streams splice tiles in. Was `tile_lut_ptr`/hypothesis, "base ~0xEA28" — see below. |
| 0x1C | 0xE71C | cmd6_byte | likely | Single byte set from the operand of map-script **cmd 6** ([[level_script_format]], handler 0x9678). Consumer not yet traced. |

## Row buffers and playfield width (2026-07-30)

The two pointers above address **different** buffers, which the earlier
`tile_lut_ptr` guess conflated:

| Range | Size | Role |
|-------|------|------|
| 0xE800–0xEA3F | 24 × 24 | ring of finished tile rows; head = `scroll_row` (0xE714) |
| 0xEA40–0xEA5F | 32 | row assembly scratch, rebuilt every map row |

`scroll_map_reader` assembles a **32-tile** row at 0xEA40, then its last act
(0x9A5B) is `LD HL,0xEA48 / LD DE,(0xE715) / LD BC,0x18 / LDIR` — copying the
**24 tiles starting at offset 8** into the ring row. Bytes 0–7 of the assembly
row are a left margin the greeble streams can address without clipping.

`scroll_vram_write` then emits `0x18` tiles per name-table row
(`LD B,0x18` at 0x9AB1, `HL += 0x20` per row at 0x9ABB), so the **playfield is
columns 0–23** and columns 24–31 belong to the status panel. That is why the
several HUD addresses in [[zanac-vdp-layout]] sit at column 24–25.

## DMA handshake protocol (confirmed by live debug, sprint 0010)

```
Per frame (order confirmed by passive write-watchpoint):
  0x948A  RES 1,(IX+0)         frame start: clear bit 1
  0x97F8  RES 0,(IX+0)         pre-clear bit 0 (belt+suspenders)
  0x9802  CALL 0x9888          compute tile row into E800 buffer
  0x9805  SET 0,(IX+0)  ←──── DMA-ready signal (Q1 answer)
  0x9809  SET 1,(IX+0)         secondary signal
  (scroll_sync spins waiting for bit 0 to clear)
  ISR (scroll_vram_write):
  0x9A86  RES 0,(IX+0)         ISR acknowledges: tile row written to VRAM
  (next frame: 0x948A clears bit 1 → cycle repeats)
```

| 0x1E | 0xE71E | base_attack_list_ptr | confirmed | 16-bit LE pointer (write-head) into the base attack list at 0xE780. `place_tile_group` writes the tile-placement RAM address of each base tile group here (confirmed writers: ~0x95FF, ~0x9631 in source). Starts at 0xE780; each entry is 4 bytes (2-byte address + 2 padding). |
| 0x20 | 0xE720 | idol_table_ptr | confirmed | 16-bit LE pointer to the per-round **idol table** (tail of the round's script data), read by the wide ground-structure handler (0x87B0) as `(E720)[(IX+0x03)] → (IX+0x1C/1D)`. Supplies per-idol tile/Y-X data **and, for orb-spawning idols, the warp-destination stream pointer** (see [[idol-warp-orbs]]). **Stored from the 2-byte operand of map-script cmd 8** ([[level_script_format]], handler 0x9699) — the same command that draws the "ROUND n" banner. |

## Notes

- Sprint 0008 incorrectly placed `stage_index` at 0xE702; live debug corrected
  to 0xE701 (stable) vs 0xE702 (incrementing row counter).
- 0xE708–0xE70E and 0xE70F were all zero or stable during the observed two
  mid-gameplay snapshots; more frames needed to characterise them.
