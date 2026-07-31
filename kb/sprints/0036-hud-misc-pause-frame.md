---
id: "0036"
status: done
range: 0x4ACE-0x4ACE,0x4C74-0x4D9F,0x4E0B-0x4E0B
strategy: forward_from_caller
budget_turns: 15
subsystems: [N, K, C, G]
---

# Sprint 0036 — HUD misc: hiscore compare, digit formatter, player snapshot, pause frame tick

> **Subsystem slice:** primary [[N-hud-and-status-display]] — close 0036 when the
> N slice lands. Also feeds [[K-game-flow-state-machine]] (`pause_frame_tick`
> 0x4E0B), [[C-entity-framework]]/[[F-player-ship-and-weapons]]
> (`player_pos_snapshot` body 0x4C91, `compare_save_hiscore` 0x4ACE), and
> delivers the unmapped DB region **0x4CF7–0x4DA5** (velocity-from-table setter)
> used by [[G-enemy-and-spawn-system]] `handler_type31`.

## Goal

Document five small routines in the 0x4Axx–0x4Exx HUD/player area that have
no KB entries but are referenced by documented symbols:

1. **`SUB_4ACE`** (0x4ACE) — `compare_save_hiscore`: 3-byte BCD compare of
   current score (E103–E105) vs hi-score (E106–E108); if current > hi-score,
   copies current score to hi-score via LDIR.
2. **`SUB_4C74`** (0x4C74) — hex nibble-pair to ASCII: splits A into high/low
   nibbles, converts each to '0'–'9'/'A'–'F', writes via `vdp_write_byte_di`.
   Used by debug/cheat display paths in `base_encounter_ctrl` and `sub_bfa0`.
3. **`LAB_4C91`** (0x4C91) — `player_pos_snapshot` body: copies E301 (player
   slot X), E303 (Y) into E129/E12A for the collision-check bounding box.
4. **`LAB_4CF7`** (0x4CF7) — **DB section with embedded code**: a `redisasm patch`
   is required before this address can be decoded.  The section starts at 0x4CF7
   and contains the velocity-from-table setter used by `handler_type31`.
5. **`SUB_4E0B`** (0x4E0B) — `pause_frame_tick`: advances the 5-bit E118
   frame counter; re-reads STOP key (row 7 bit 4); detects the second STOP press
   (E118 bit 7 transition) and calls `restore_sound` (0x520E); returns carry
   when STOP-cycle is complete.

## Inputs

- `kb/symbols/0x4000-init/game_over_handler.md` — calls 0x4ACE
- `kb/symbols/0x4900-hud/player_pos_snapshot.md` — calls 0x4C91 and 0x4CF7
- `kb/symbols/0x4900-hud/update_fire_display.md` (pause_handler) — calls 0x4E0B
- `kb/symbols/0x8000-enemy/handler_type31_stealth_tracker.md` — calls 0x4CF7
- `kb/guides/redisasm-protocol.md` — required for 0x4CF7 patch
- Source lines 1340–1360 (0x4ACE), 1506–1525 (0x4C74–0x4C91),
  1560–1580 (0x4CF7 DB block), 1629–1660 (0x4E0B)

## Verification plan

### Step 1 — Decode SUB_4ACE (static)

Read source lines 1340–1358.  Confirm the 3-byte BCD compare: SBC A,(HL) loop
over 3 bytes; if carry set (current < hi), return; else LDIR 3 bytes.

### Step 2 — Decode SUB_4C74 (static)

Read source lines 1506–1522.  The two-entry structure (4C74 = high nibble first,
4C7D = low nibble only) should map to the standard hex-byte-to-ASCII pattern.

### Step 3 — Decode LAB_4C91 (static)

Read source lines 1521–1540.  Map the player snapshot: which RAM addresses are
read and where the results go (E129, E12A expected).

### Step 4 — redisasm patch for 0x4CF7 DB block

Identify the `--before` and `--after` anchors for the DB block starting at
0x4CF7 and ending before `SUB_4DA5` (0x4DA5):

```bash
.venv/bin/python tools/redisasm.py patch \
    --before "RET.*; 0x4cf6" \
    --after  "SUB_ram_4da5:"  \
    --start  0x4CF7  --end  0x4DA5
```

After patching, re-read the decoded instructions to understand the
velocity-table lookup used by handler_type31.

### Step 5 — Decode SUB_4E0B (static)

Already read in sprint 0032 context (lines 1629–1658).  Write the symbol file
based on the known analysis: E118 increment (AND 0x1F + preserve bit 7), SNSMAT
row 7 re-read, two-phase STOP detection, call to `restore_sound` on exit.

## Key questions

- Does the 0x4CF7 DB block also contain the velocity table data (at 0x4D47+),
  or is the table embedded in a separate region?
- What registers does 0x4CF7 expect on entry from `handler_type31` (E in
  `vel_param` is confirmed; what else)?
- Does `compare_save_hiscore` update the on-screen hi-score display, or only
  the RAM bytes?

## Expected KB entries

- `kb/symbols/0x4000-init/compare_save_hiscore.md` — `SUB_4ACE` (0x4ACE)
- `kb/symbols/0x4900-hud/hex_byte_to_ascii.md` — `SUB_4C74` (0x4C74)
- `kb/symbols/0x4900-hud/player_pos_snapshot.md` — update with correct body desc
- `kb/symbols/0x4900-hud/velocity_from_table.md` — decoded 0x4CF7 block
- `kb/symbols/0x4900-hud/pause_frame_tick.md` — `SUB_4E0B` (0x4E0B)

## Summary (closed by later slices — 0058)

All five routines are documented; 0036 was superseded piecemeal by the N/K/F
subsystem slices and is closed here as an accounting sprint. Mapping of the five
originally-scoped items to where they actually landed:

| # | Routine | Status | KB entry (owning sprint) |
|---|---------|--------|--------------------------|
| 1 | `SUB_4ACE` compare_save_hiscore | done | `kb/symbols/0x4900-hud/compare_save_hiscore.md` (0046) |
| 2 | `SUB_4C74` hex→ASCII | done | `kb/symbols/0x4900-hud/render_hex_byte.md` (0047, subsystem **N**) |
| 3 | `LAB_4C91` player_pos_snapshot body | done | `kb/symbols/0x4900-hud/player_pos_snapshot.md` (0044) |
| 4 | `LAB_4CF7` velocity-from-table (DB block) | done | disassembled + named `set_velocity_from_dir.md` (0048); the 0x4CF7–0x4DA4 DB block became code + `dir_angle_thresholds`/`dir_remap_table`/`vel_dir_table` |
| 5 | `SUB_4E0B` pause_frame_tick | done | documented inline in `kb/symbols/0x4900-hud/update_fire_display.md` = `pause_handler` (0x4DA5, 0032); 0x4E0B is the counter-advance / STOP re-read helper it calls at 0x4DF7 |

### Relation to subsystem N

Item 2 (`render_hex_byte` 0x4C74) and the adjacent `data_4b2a`/`score_award_table`
(0x4AEA) questions this sprint raised were fully resolved by the **N slice**
(sprint 0047): `0x4C74` is a confirmed N render primitive (shared with the ALC
display, [[I-alc-adaptive-difficulty]]), `0x4AEA` is `score_award_table` (not
glyphs), and `data_4b2a` (0x4B2A–0x4B82) is a separate unreferenced table parked
under [[I-alc-adaptive-difficulty]]. See [[N-hud-and-status-display]] "Sprints"
which already records "Sprint 0036's N items … are resolved here." So 0036 owned
no residual N work at close.

Items 1/3/4 belong to K/C/F (hiscore, collision snapshot, weapon velocity) and
item 5 to K/input (pause) — none of these remain open.

