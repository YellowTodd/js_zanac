---
letter: D
title: Scroll & Tile Rendering
coverage: done
status: done
---

# D — Scroll & Tile Rendering

## Role

The vertically-scrolling background engine: advances the scroll position at the
controlled velocity, reads the level map stream column-by-column, builds tile
groups into the VRAM name table, and keeps the on-screen tile window in sync as
the map flows past. Consumes level data produced/decoded by
[[E-level-data-and-decompression]] and is paced by [[B-frame-render-pipeline]].
The base-encounter deceleration/stop behaviour bridges into
[[G-enemy-and-spawn-system]].

## Key routines

| Addr | Name | Conf | Notes |
|------|------|------|-------|
| 0x946E | `build_tile_screen` | likely | run the column step ×24 (fill whole buffer) |
| 0x9480 | `scroll_velocity_ctrl` | likely | accel/decel/stop velocity; falls into 0x94C3 |
| **0x94C3** | **`map_script_step`** | **confirmed** | **row-triggered map-script interpreter (13-cmd table @0x94EB)** |
| 0x95A8 | `load_stream_slots` | likely | load map-stream slots (cmd 5) |
| 0x95C0 | `init_stream_slot` | likely | init one stream slot |
| 0x95ED | `place_tile_group` | likely | emit a tile group |
| 0x97D5 | (`map_script_step` converge) | confirmed | read next row trigger, advance PC |
| 0x97E3 | `scroll_precompute` | confirmed | non-command path: build one tile column |
| 0x986E | `copy_tile_column` | likely | copy one tile column |
| 0x9888 | `scroll_map_reader` | likely | per-column tile assembler (live-confirmed) |
| 0x9A79 | `scroll_vram_write` | likely | write tiles to VRAM (per-VBLANK) |
| 0x9AA6 | `scroll_vram_inner` | likely | inner VRAM loop |
| 0x9AE4 | `scroll_sync` | likely | keep window aligned |
| 0x9B22 | `check_col_clear` | confirmed | column-cleared test |

Also: `map_script_init` (`sub_940c`/`sub_9405` 0x9405–0x9432) starts the
interpreter on a script; `sub_9433` (cmd 9 target) jumps to a new round's script
via [[resolve_round_from_ptr]] (`stage_stream_ptr_table` 0x945C).

## State / data

- `scroll_state` (0xE700) — scroll flags, velocity, and the map-script
  program-counter (0xE702 row / 0xE704 PC / 0xE706 trigger / 0xE701 round).
- `level_script_format` (0xA65C–0xB7A5) — the row-triggered map-script bytecode
  and 13-command table.

## Guides

- `zanac-vdp-layout`, `graphics-data`.

## How it fits together

```
build_tile_screen / scroll_velocity_ctrl  →  map_script_step (0x94C3)
   row++ ; if row == next_cmd_row:  dispatch map command (0x94EB table)
                                     └─ ends JP 0x97D5 → load next trigger, loop
           else:                    scroll_precompute (0x97E3)
                                     └─ scroll_map_reader (0x9888) builds 1 column
                                        → 0xE800 buffer, raise DMA flag (E700 b0/b1)
VBLANK ISR → scroll_vram_write (0x9A79) → scroll_vram_inner → VDP name table
```

## Gaps / open questions

- Per-round *content* of the script data 0x9B64–0xBE27 belongs to subsystem E.
- Consumer of 0xE71C (cmd 6); byte-exact operand grammar of cmds 0/1/3/4/A.

## Sprints

0008 (scroll engine), 0009 (tile stream), 0029 (script format),
0010 (live state), 0033 (credits reuse), **0056 (map-script interpreter — closed)**.
