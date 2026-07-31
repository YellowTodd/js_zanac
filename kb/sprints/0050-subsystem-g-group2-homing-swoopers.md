---
id: "0050"
status: done
range: 0x7d0f-0x7f1f,0x8296-0x82cf,0x84dd-0x852e,0x8635-0x869d
strategy: subsystem_slice
budget_turns: 40
subsystems: [G]
---

# Sprint 0050 — Subsystem G group 2 (homing / swoopers / bullets, types 20–38)

## Goal

Second ~12-types slice. Types 31/33/34 (stealth) and 35 (projectile) already
done; this group covers the rest of 20–38:

| Types | Handler | Name |
|-------|---------|------|
| 20 | 0x8668 | `handler_type20_lead_homing` |
| 21 | 0x8635 | `handler_type21_light_bar` |
| 22–23 | 0x7d0f | `handler_type22_veybar` (shared body 0x7d4c, fire sub 0x7d8c) |
| 24–25 | 0x7db4 | `handler_type24_veybar_fast` (joins 0x7d4c) |
| 26–27 | 0x7de2 | `handler_type26_edge_swooper_a` (anim 0x7e68) |
| 28–29 | 0x7e78 | `handler_type28_edge_swooper_b` (anim 0x7e70) |
| 30,32 | 0x7e9c | `handler_type30_ground_swooper` (spawns paired child) |
| 36 | 0x8296 | `handler_type36_flashing` |
| 37 | 0x84dd | `handler_type37_lead_bullet` |
| 38 | 0x8501 | `handler_type38_burst_fragment` |

## Inputs

- `kb/data/entity_jump_table.md`; group-1 handlers (0049).
- Helpers: 0x4cf7 (set_velocity_from_dir), 0x4c8b (player_pos_snapshot),
  0x4c91 (player snapshot sub), 0x43c0 (prng_next), 0x71da/0x71c5/0x71f6,
  0x4898/0x44ba/0x44a6, 0x8ddb, 0x7904 (box hit-sub), 0x5189 (play_sfx).
- Source: 0x7d0f–0x7f1f, 0x8296–0x82cf, 0x84dd–0x852e, 0x8635–0x869d.

## Verification plan

`tools/sprint0050_verify.py` — inject each type into a free slot, run init,
read back IX fields vs decode; read anim tables 0x7e68/0x7e70 from ROM.

## Summary (filled at end)

**Group 2 (types 20–30, 32, 36–38) done ✓. 12/12 live checks** (2 anim tables +
10 handler-init captures, `tools/sprint0050_verify.py`).

### Confirmed (live capture)

| Handler | Key evidence |
|---------|--------------|
| `handler_type20_lead_homing` (20) | sat=1C bflags=0B tgt_y=FF y_acc=0C; vx via prng |
| `handler_type21_light_bar` (21) | sat=18 bflags=03; dir from +0x1a; colour flicker |
| `handler_type22_veybar` (22–23) | sat=84 col=83 bflags=09 y_acc=14; fires type-37 |
| `handler_type24_veybar_fast` (24–25) | sat=84 bflags=1B x_acc=10 col=89 (joins veybar body) |
| `handler_type26_edge_swooper_a` (26–27) | anim ptr +0x11=68 bflags=0F child +0x1d=25; runs anim (sat→B0) |
| `handler_type28_edge_swooper_b` (28–29) | anim ptr +0x11=70 bflags=0F child +0x1d=3B |
| `handler_type30_ground_swooper` (30/32) | sat=EC bflags=01 vy_frac=80; spawns paired child type own+1 (→31/33) |
| `handler_type36_flashing` (36) | sat=34 hp(+0x19)=10; colour XOR 0x0E flicker |
| `handler_type37_lead_bullet` (37) | sat=1C col=8F bflags=03; aims via player_pos_snapshot |
| `handler_type38_burst_fragment` (38) | sat=1C bflags=03; dir from +0x1a (umber burst link) |
| `edge_swooper_a_anim` / `_b_anim` | 0x7e68/0x7e70 = pats 43–46, col 0x8E / 0x87 |

### New symbols / data

- 10 handler files (0x8000-enemy/), 2 anim-table data files (kb/data/).
- `tools/sprint0050_verify.py`.

### Notes

- The `+0x1a` "spawn param" threads through the burst/bar family: umber writes
  [[umber_burst_param_table]] → type-38 fragment / type-21 light_bar read it
  `& 0x0F` as a direction for `set_velocity_from_dir`.
- Ground swooper (30/32) is a two-part enemy: copies its 13-byte header into a
  paired stealth-tracker child (type own+1) via LDIR, then aligns to the player.
- 2 more byte-neutral anim tables (0x7e68/0x7e70) added to
  `db-sections-with-code.md`; source relabel still deferred with group 1's.

`zanackb validate` 0 errors. `source/zanac.asm` unchanged.
