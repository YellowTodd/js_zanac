---
letter: A
title: Boot & Hardware Init
coverage: complete
status: done
---

# A — Boot & Hardware Init

## Role

Everything from ROM entry until the title screen is ready: cartridge header,
slot detection, VDP/PSG hardware setup, screen-mode selection, and the one-time
RAM/state initialisation. Runs once per power-on (and parts re-run on each
new game via the flow state machine, [[K-game-flow-state-machine]]).

## Key routines

| Addr | Name | Conf | Notes |
|------|------|------|-------|
| 0x4000 | `rom_header` | confirmed | cartridge header / init vector |
| 0x4010 | `cold_start` | confirmed | top-level boot entry |
| 0x40BA | `reset_entities` | confirmed | clears entity slot pool (shared with [[C-entity-framework]]) |
| 0x412A | `load_bg_level` | likely | kicks off level load (shared with [[E-level-data-and-decompression]]) |
| 0x428A | `init_screen_mode` | confirmed | Screen 2 setup: VDP regs, charset load, clear name table, hide sprites, clear entity table |
| 0x42BA | `init_vdp_regs` | confirmed | writes VDP R0–R7 from `vdp_init_table` (RDVDP then WRTVDP×8) |
| 0x42CF | `vdp_init_table` | confirmed (data) | VDP register seed values (live-verified) |
| 0x4E45 | `map_page2` | confirmed | mirror the cartridge slot into page 2 (ENASLT) |
| 0x4E50 | `detect_slot` | confirmed | resolve cartridge slot via RSLREG + EXPTBL |

Also called once from `cold_start`: `init_psg_freq_table` (0x513F — builds the PSG
note table; see [[O-sound-system]]).

Utilities decoded in the 0x43xx range during this slice (cross-cutting, not boot
proper): `mul_a_e` (0x4317, 8×8→16 multiply), `div_hl_e` (0x4329, 16÷8
round-to-nearest divide; used by collision distance), `prng_next` (0x43C0,
advances `prng_state` — used by [[G-enemy-and-spawn-system]]).

> **Note:** `0x4343` (formerly `read_options`) was reassigned out of this
> subsystem — it is the per-frame **player-input poll** `read_player_input`, not
> a boot option reader. See [[F-player-ship-and-weapons]].

## State touched

- `game_state_block` (0xE100) capability/option bits — see [[K-game-flow-state-machine]].
- VDP shadow regs in sysvars (RG0SAV…RG7SAV).

## Guides

- `zanac-vdp-layout`, `vdp-tms9918a`, `vdp_init_table` (data).

## Status: fully documented ✓ (sprint 0040)

Every routine whose primary home is A is decoded against correct BIOS semantics
and **live-confirmed** (`init_vdp_regs`, `init_screen_mode`, `detect_slot`,
`map_page2` traced in openMSX; `cold_start`/`reset_entities`/`vdp_init_table`
already confirmed). No `hypothesis` entries and no unmapped DB regions remain in
A's address range — the two embedded-code DB blocks (0x4317, 0x43C0) were
disassembled and KB'd this slice.

Remaining caveats are **boundary routines owned by other subsystems**, not A:

- `load_bg_level` (0x412A) is `likely` but belongs to [[E-level-data-and-decompression]].
- `cold_start` also calls into [[O-sound-system]] (`init_psg_freq_table`,
  `play_sound_event`), [[J-title-screen]] (`title_intro_seq`, `title_screen_init`),
  and [[B-frame-render-pipeline]] (`enable_display`, `wait_frames`) — all already
  documented in their own subsystems.

## Sprints

Done: 0001 (bootstrap), 0002 (bios survey), 0003 (vdp tables), 0040 (subsystem-A
boot/init pass — BIOS-call corrections, `read_options` → `read_player_input`).
