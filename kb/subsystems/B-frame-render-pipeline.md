---
letter: B
title: Frame / Render Pipeline
coverage: done
status: done
---

# B — Frame / Render Pipeline

## Role

The per-frame substrate every other subsystem rides on: the VBLANK interrupt
handler, VDP interrupt enable/disable gating, the frame-wait primitives, the
sprite-attribute-table (SAT) shadow → VRAM transfer, and the low-level VDP
write helpers. Also hosts the PSG sound tick that the ISR drives
([[C-entity-framework]] and the sound system both depend on this timing).

## Key routines

| Addr | Name | Conf | Notes |
|------|------|------|-------|
| 0x43DA | `vblank_isr` | confirmed | HTIMI/HKEYI hook; per-frame top of pipeline |
| 0x43F8 | `sat_dma_to_vram` | confirmed | ISR segment: SAT shadow 0xE000 → VRAM 0x3B80 (normal + 5S flicker) |
| 0x42D7 | `disable_display` | confirmed | blank screen (R1 BL bit 6) |
| 0x42E2 | `enable_display` | confirmed | unblank screen (R1 BL bit 6) |
| 0x42ED | `vdp_int_disable` | confirmed | gate VDP interrupts off (R1 IE bit 5) |
| 0x42F8 | `vdp_int_enable` | confirmed | gate VDP interrupts on (R1 IE bit 5) |
| 0x4306 | `wait_one_frame` | confirmed | spin to next VBLANK |
| 0x5BEC | `wait_frames` | confirmed | wait N frames |
| 0x4E7B | `sub_4e7b` (psg_sound_tick) | confirmed | ISR-driven PSG/fire-sound tick |
| 0x48A9 | `sprite_shadow_push` | confirmed | motion+anim then SAT append (shared [[C-entity-framework]]) |
| 0x48B8 | `sprite_sat_write` | confirmed | append 4-byte SAT entry via 0xE122 |
| 0x5BDD | `tile_to_vram_addr` | confirmed | name-table address calc |
| 0x5BFC | `vdp_write_byte_di` | confirmed | guarded single-byte VRAM write |
| 0x5C25 | `vdp_set_addr_write` | confirmed | inline null-terminated string → name table |
| 0x9393 | `gameplay_frame_loop` | confirmed | per-frame gameplay driver (shared [[K-game-flow-state-machine]]) |

## State

- `frame_counter` (0xE1F8); SAT shadow walk pointer (0xE122) → SAT shadow at 0xE000.

## Guides

- `vdp-tms9918a`, `zanac-vdp-layout`.

## Gaps / open questions

None — all routines `confirmed` (sprint 0043). `vdp_set_addr_write` was
confirmed in 0042; the SAT-DMA path is now its own entry (`sat_dma_to_vram`).

## Sprints

0004 (vblank handler), 0018 (vblank pipeline), 0042 (vdp_set_addr_write),
0043 (confirm all + split SAT-DMA).
