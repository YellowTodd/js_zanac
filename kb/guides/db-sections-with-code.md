# DB sections in zanac.asm that contain running code

The Ghidra disassembler could not statically decode several regions and emitted
them as `DB` (raw byte) blocks. Live openMSX analysis confirms these are valid
Z80 code reachable via computed jumps or indirect `JP HL` sequences that the
static disassembler could not trace.

---

## Status summary

| Category | Items |
|----------|-------|
| Patched and ROM-verified (✓) | **12 blocks** |
| Confirmed DB blocks containing code — pending patch | 0 |
| Decoded but missing label definitions | **1** (0x45A0 in collision block) |

---

## All patched DB blocks (✓ ROM-verified)

| ROM address | KB entry | Content |
|---|---|---|
| 0x44A6–0x453D | `entity_post` | Dispatch epilogue: sprite push + collision routing |
| 0x4560–0x4648 | `collision_routine` | Two routines: `hitbox_check_iy` (0x4560–0x459F) and `hitbox_setup_ix` (0x45A0–0x45C8); size table data at 0x45C9–0x45E8 kept as DB. **0x453E–0x455F kept as DB but contains code — see pending section.** |
| 0x4898–0x4995 | `entity_update` family | Behavior-flag dispatch + motion/animation/homing subs (credits data at 0x4775–0x4897 kept as DB) |
| 0x4C8B–0x4CF6 | `player_pos_snapshot` | Player Y/X snapshot; vertical collision distance calc |
| 0x4E7B–0x513E | `sub_4e7b` (psg_sound_tick) | ISR fire-sound trigger + PSG voice slot scan |
| 0x8094–0x819C | entity handlers | Ground-structure projectile subtable dispatch (types 46–55) |
| 0x819D–0x81D0 | entity handlers | Type-56 handler (sig_single pickup/missile) |
| 0x81D1–0x8947 | entity handlers | Remaining entity handlers |
| 0x453E–0x455F | `LAB_ram_453e` | Entity class-lookup: IX/IY types → 0x716B → class; overwrites IX/IY+0 with class; entity_post exit target |
| 0x5D02–0x5D19 | `LAB_ram_5d02` | Decompressor inner loops: reads D, C, B×A counts from HL stream; calls SUB_ram_5d1a; JRs back to LAB_ram_5cdd |
| 0x8BF5–0x8F5D | `LAB_ram_8bf5` | Sound engine (~873 bytes): PSG voice tick, note dispatch, vibrato, envelope; sub-entry `LAB_ram_8ddb` (entity sound init, widely called); sub-entry `LAB_ram_8e1f` (play_sound_event target) |
| 0xBF9C–0xBF9F | `LAB_ram_bf9c` | Tiny stub: `DEC (IX+0x26)` / `RET` — decrements IX+0x26 counter |
| 0x4317–0x4328 | `mul_a_e` | 8×8→16 unsigned multiply (HL = A × E) |
| 0x4329–0x4342 | `div_hl_e` | 16÷8 divide, round-to-nearest quotient in L; called by 0x4CDB |
| 0x43C0–0x43D1 | `prng_next` | 16-bit PRNG advance (R-register seeded); writes `prng_state` 0xE12B |
| 0x4A6A–0x4A73 | `add_score_for_subtype` (0063) | 10-byte prologue: `A = (0x4B29 + (IX+0x18))` → falls through to `add_score`; the long-lost reader of `data_4b2a` (= `structure_award_index_table`) |

> **Known overlapping decode (found by the 0063 audit):** the byte 0xDD at
> **0x8E14** is both the displacement of the preceding `DJNZ 0x8df2` (0x8E13,
> rel −0x23) *and* the first byte of `handler_type80_base_damage`'s
> `BIT 7,(IX+0)` when entered via the entity jump table. The asm shows the
> DJNZ view, so the lines at 0x8E15/0x8E17 (`RLC B` / `LD A,(HL)`) are phantom
> decodes of the handler's first instruction. ROM bytes are identical either
> way; do not "fix" without deciding which execution path to privilege.

---

## Previously pending — now done ✓

### Block A — Collision detection (0x4560–0x4648)

Contents decoded in sprint 0030. Sprint 0021's partial decode was wrong (see sprint 0030 summary).

| ROM address | Subroutine | Description |
|-------------|-----------|-------------|
| 0x4560–0x459F | `hitbox_check_iy` | Tests IY entity's sprite against IX's pre-computed bounds (BC / BC'); returns carry if overlap on both axes |
| 0x45A0–0x45C8 | `hitbox_setup_ix` | Computes IX entity hitbox from sat_name and size table; outputs BC = (Y_bottom, Y_top), BC' = (X_right, X_left) |
| 0x45C9–0x45E8 | `collision_size_table` | **Data** (KB'd) — 32-byte hitbox half-size pairs indexed by `sat_name >> 1`; kept as DB |

**Correction from sprint 0021:** The `LD HL,0x716B` attributed to 0x4560 was a misread. ROM bytes at 0x4567 are `LD HL,0x45C9` (the size table). There is no collision class lookup in these routines.

**0x453E–0x455F is code, now patched ✓** `LAB_ram_453e` added. The bytes decode as the entity class-lookup routine (LD A,(IX+0) → AND 0x7F → cache to IX+0x18 → look up 0x716B → overwrite IX/IY+0 with class → RET). Entity_post jumps here (not CALLs) to translate types to classes before/after the hitbox check.

**Command used:**
```bash
.venv/bin/python tools/redisasm.py patch \
    --before "; 0x453d" \
    --after  "SUB_ram_4649" \
    --start  0x4560 --end 0x4649
```

---

### Block B — entity_update family (0x4898–0x4995)

Contents decoded in sprint 0021 (entity_table.md, behavior_flags dispatch):

| ROM address | Subroutine | Description |
|-------------|-----------|-------------|
| 0x4898 | entity_update | Dispatch on IX+0x0C bits: BIT3→0x4942, BIT4→0x496B, BIT0→0x48DE, BIT1→0x48F8, BIT2→0x4912; then SAT push to 0xE122 |
| 0x48D0 | entity_clear | Zero IX+0x00..IX+0x17 (24 bytes) via PUSH IX/POP HL/LD(HL),0/LDIR; IX+0x18..0x1F persist |
| 0x48DE | Y_motion_sub | (IX+1:6) += (IX+9:8); clamp Y; if Y≥208 → entity_clear |
| 0x48F8 | X_motion_sub | (IX+2:7) += (IX+11:10); clamp X; if X≥209 → entity_clear |
| 0x4912 | anim_sub | DEC IX+0x0D; on 0 reload from IX+0x0E; advance IX+0x0F; read (sat_name,sat_color) from IX+0x11:0x12 table; wrap at IX+0x10 |
| 0x4942 | Y_homing_sub | Add/sub IX+0x15 to vy (IX+8:9) toward target IX+0x13; IX+0x17 iterations |
| 0x496B | X_homing_sub | Add/sub IX+0x16 to vx (IX+10:11) toward target IX+0x14; IX+0x17 iterations |

Note: 0x4775–0x4897 (credits script data) is genuine data and was automatically
preserved as DB by the prefix-aware patch logic.

**Command used:**
```bash
.venv/bin/python tools/redisasm.py patch \
    --before "JP.*0x46e0" \
    --after  "SUB_ram_4996" \
    --start  0x4898 --end 0x4996
```

---

## Previously missing labels — now inserted ✓

All five label definitions were added with `add-label --addr 0xADDR` (no
`--before` needed; located by ROM address comment).

| Address | Label | First instruction | Context |
|---------|-------|-------------------|---------|
| 0x7F73 | `LAB_ram_7f73:` | `LD A, (IX+0x04)` | Common epilogue for player-tracking entities (flicker + entity_update + entity_post) |
| 0x7F84 | `LAB_ram_7f84:` | `LD A, (0xe301)` | Type-31/33 stealth tracker running entry |
| 0x7F99 | `LAB_ram_7f99:` | `BIT 7, (IX+0x00)` | Type-34/65/66 init check |
| 0x730B | `LAB_ram_730b:` | `LD HL, 0xe14c` | Fire weapon life-timer |
| 0x7548 | `LAB_ram_7548:` | `LD E, A` | Fire weapon switcher |

**Still missing — sprint 0030:**

| Address | Proposed label | Context |
|---------|----------------|---------|
| 0x45A0 | `hitbox_setup_ix` | Already decoded in sprint 0030 and documented in collision_routine.md; just needs `add-label --addr 0x45A0` in the patched block |

---

## Previously pending DB blocks — now patched ✓

All five candidate blocks from KB cross-referencing (sprints 0028–0030) were resolved in session after sprint 0030.

| Block | Status | Notes |
|-------|--------|-------|
| 0x453E–0x455F | **Patched** | Entity class-lookup code; `LAB_ram_453e` added |
| 0x5D02–0x5D19 | **Patched** | Decompressor inner-loop code; `LAB_ram_5d02` added |
| 0x8BF5–0x8F5D | **Patched** | Full sound engine; `LAB_ram_8ddb`, `LAB_ram_8e1f` added |
| 0xBF9C–0xBF9F | **Patched** | `DEC (IX+0x26)` / `RET` stub; `LAB_ram_bf9c` added |
| 0xBE27 | **Already decoded** | 0xBE27 is just after the huge 0x9B64–0xBE24 data block; no patch needed |
| 0xBFAB | **Already decoded** | 0xBF9C block is only 4 bytes (ends 0xBF9F); 0xBFAB is in decoded code |
| 0x8983–0x8A15 | **Patched (0052)** | `handler_type72_base_core`; data tail 0x8A16–0x8A25 = [[base_core_anim]]; `LAB_ram_8983` added |
| 0x8A5A–0x8BC9 | **Patched (0052)** | `handler_type73_base_segment` (368 B); `LAB_ram_8a5a` added |

---

## Why Ghidra missed these

All reachable via **indirect control flow**:
- `entity_post` (0x44A6): `PUSH BC; JP HL` — Ghidra cannot trace JP HL.
- `sub_4e7b` (0x4E7B): ISR installed at runtime (H_TIMI hook at 0xFD9A).
- Entity handlers (0x8094+): `JP HL` after loading HL from the entity_jump_table.
- Collision routines (0x4560): reached from entity_post via computed dispatch; the preceding DB block (0x453E–0x455F, entity class-lookup code) confused the disassembler — Ghidra saw no opcode entry to 0x453E and marked the whole region as data.
- entity_update (0x4898): entry point sits inside the credits text data block (0x4775–0x4897), which Ghidra classified entirely as data.
- `sub_730B`, `sub_7548`, `0x7F73`, `0x7F84`, `0x7F99`: all entered via indirect calls/jumps from dispatch tables or computed gotos (`EX (SP),HL; RET` trick for fire weapon dispatch, inline jump tables for entity handlers).

## What remains as genuine data

- ~~Entity-type collision table at 0x453E–0x455F~~ — **reclassified as code** (see Pending section)
- Credits text data at 0x4775–0x4897 (keep as DB before 0x4898) — KB'd 0063:
  `credits_control_table` (0x4775) + `logo_tile_rows` (0x4827)
- ~~Vertical collision distance table at 0x4CF7–0x4DA4~~ — **was code**:
  `set_velocity_from_dir` + dir tables (patched 0048, KB'd 0063)
- Fire weapon direction/velocity tables (0x7758, 0x7761, 0x778F, 0x807C, 0x8084, 0x8087)
- Animation tables (0x84D1, 0x86F3)
- Compressed graphics, sound/music data, spawn velocity tables

---

## Unmapped large DB regions (>16 bytes)

Inventory of `DB` blocks larger than 16 bytes that are **not yet covered by a KB
data/symbol entry** — either genuine data still to be catalogued or possibly
undecoded code. Generated by scanning `source/zanac.asm` for contiguous DB runs
and subtracting blocks already owned by a KB entry. Sizes are byte counts.
Subsystem letters refer to `kb/subsystems/`. CLAUDE.md carries the short summary;
this table is the authoritative detail.

| Region | Bytes | Subsystem | Hypothesis | How to attack |
|--------|-------|-----------|------------|---------------|
| ~~0x9B64–0xBE27~~ | 8899 | E | **MAPPED ✓ (sprint 0037)** — full carve-up in `kb/guides/level-data-block-map.md`: tile-column/greeble data (0x9B64–0xA443 region 1, 0xB7A6–0xBE26 region 2, pointed to by map-script cmd 1/2/3/B), `tile_tables` (0xA444–0xA653), 9 map scripts (0xA65C–0xB7A5 via ptr table 0x945C), round/boss text (0xBBxx/0xBCB2), `spawn_table` (0xBE76). PRNG false-readers (0xB007/0xB78E/0xB8FD) noted. | done — only per-round greeble-record field semantics remain (data) |
| ~~0x5236–0x5A11~~ | 2011 | O | **CATALOGUED ✓ (sprint 0057)** — 27-event pointer table (0x5234) + all events classified (music/SFX/purpose/chaining) in `kb/guides/sound-engine.md`. Stage BGM = computed `3+(E10F>>2)`; explosion = ev18; chaining `0x87` (ev7→1, 12→5). | done — only byte-exact per-track "score" left (content) |
| ~~0x8A5A–0x8BCA~~ | 368 | G | **PATCHED ✓ (sprint 0052)** — was code: `handler_type73_base_segment` (see the patched-blocks table above). | done |
| ~~0x9678–0x97D5~~ | 349 | D | **PATCHED ✓ (sprint 0056)** — was code: map-script command handlers 6–12 (`map_script_step`/`level_script_format`), incl. the "ROUND n" banner (cmd 8). Residual data marked: `round_banner_text`, `glyph_col_data_973e`, `cmd11_index_table`. | done |
| ~~0x4CF7–0x4DA5~~ | 174 | C/F | **RESOLVED ✓ (0048 + 0063)** — was code: `set_velocity_from_dir` (0x4CF7, patched 0048) followed by data now KB'd: `dir_angle_thresholds` (0x4D42), `dir_remap_table` (0x4D45), `vel_dir_table` (0x4D65). | done |
| ~~0x8983–0x8A26~~ | 163 | G | **PATCHED ✓ (sprint 0052)** — was code: `handler_type72_base_core` (0x8983); data tail = `base_core_anim` (0x8A16, KB'd). | done |
| ~~0x4AEA–0x4B83~~ | 153 | N | **RESOLVED ✓ (0047 + 0063)** — `score_award_table` (0x4AEA–0x4B29, 3-byte BCD awards) + `structure_award_index_table` (0x4B2A–0x4B82, the former `data_4b2a`): its reader was hidden in the 10-byte code-in-DB block at 0x4A6A (`add_score_for_subtype`, patched 0063). | done — live verify in 0065 |
| ~~0x9537–0x95A8~~ | 113 | D | **PATCHED ✓ (sprint 0056)** — was code: map-script command handlers 3–5 (`map_script_step`/`level_script_format`). The `0x94EB` inline jump table is now `map_cmd_jump_table` (data). | done |
| ~~0x93AB–0x93E3~~ | 57 | **G** | **DECODED ✓ (0065, live)** — [[base_attack_patterns]]: 8 LE pointer words (0x93BB…) + 8 variable-length descriptors of **3-byte `(rate0,rateM,rate3)` records, `0x00`-loop** (interpreter 0x8BF5); read by `base_attack_spawn` (0x8FDE) round-robin via cursor 0xE717. Confirmed in a round-1 base fight. | done (confirmed) |
| ~~0x4317–0x4343~~ | 44 | util | **PATCHED ✓ (sprint 0040)** — was code: `mul_a_e` (0x4317, 8×8→16 multiply) + `div_hl_e` (0x4329, 16÷8 round-to-nearest divide). | done |
| ~~0x43C0–0x43D1~~ | 18 | util | **PATCHED ✓ (sprint 0040)** — `prng_next` (advances `prng_state` 0xE12B via the R register). | done |
| ~~0x51F0–0x5207~~ | 24 | O | **DECODED ✓ (0065)** — [[psg_period_base_table]]: 12 LE base periods (one chromatic octave) expanded to 0xF200 by `init_psg_freq_table` (0x5147). | done (confirmed) |
| ~~0x9302–0x9314~~ | 19 | N/G | **DECODED ✓ (0065, live)** — [[base_clear_award_index_table]]: score-award indices by base-progress counter `(IX+0x57)&0x1F`, read at 0x91A9 → `add_score` when the base's segment count `E152` hits 0. Confirmed: index 0x0A loaded for counter 0 = ROM `0x9302[0]`. | done (confirmed) |
| ~~0x43C0–0x43D2~~ | 18 | J/A | **Stale duplicate** of the 0x43C0–0x43D1 row above (patched `prng_next`, sprint 0040). | done |
| ~~0x945C–0x946E~~ | 18 | D | **MAPPED ✓** — `stage_stream_ptr_table` (KB'd; rounds 8→0 stream starts, used by `resolve_round_from_ptr`). | done |

> **Superseded by `tools/coverage_audit.py` (sprint 0063).** This table is kept
> as history; the authoritative unknown-bytes list is now the audit tool's
> output. Post-0063 remaining unknowns: 0x51F0 (24 B, → 0065), 0x5236–0x5A10
> (2011 B, → 0064), 0x9302 (19 B, → 0065), 0x93AB (57 B, → 0065),
> 0x9B64–0xA443 + 0xB7A6–0xBE26 (3937 B greeble/tile-column records, → 0062),
> 0xA654–0xA65B (8 B, → 0062/0066).

## Byte-neutral mis-decoded data tables — RESOLVED ✓ (sprint 0053)

Seven enemy-handler data tables used to render as **instructions** in
`source/zanac.asm` (they round-tripped to the same ROM, so `verify` passed, but
were semantically data, and two of them absorbed the leading `DD` of the handler
that followed, mis-rendering its `BIT 7,(IX+0)` entry). All converted to labelled
`DB` blocks via the new `redisasm data` command (sprint 0053); ROM byte-identical.

| Region | Bytes | KB entry | Label / absorbed entry re-decoded |
|--------|-------|----------|-----------------------------------|
| 0x77EA–0x7807 | 30 | [[proto_box_type_table]] | label `proto_box_type_table:` |
| 0x7808–0x7825 | 30 | [[proto_box_sat_table]] | (same DB run; 0x7826 `handler_type4_box` entry re-decoded ✓) |
| 0x79B7–0x79BD | 7 | [[umber_burst_param_table]] | label `umber_burst_param_table:` |
| 0x7AF7–0x7B06 | 16 | [[base_spawner_spawn_table]] | label; 0x7B07 `handler_type12_teruzo` entry re-decoded ✓ |
| 0x7B7B–0x7BEA | 112 | [[teruzo_motion_tables]] | label `teruzo_motion_tables:` |
| 0x7E68–0x7E6F | 8 | [[edge_swooper_a_anim]] | label `edge_swooper_a_anim:` |
| 0x7E70–0x7E77 | 8 | [[edge_swooper_b_anim]] | (same DB run, after a_anim) |

Mapped large DB blocks (not unknowns, excluded above): graphics assets
0x5D2C–0x70B7 (`gfx_*`), `spawn_table` (0xBE76), `entity_jump_table` (0x70B9),
and the credits script 0x4775–0x4897 — all have KB entries.

To regenerate after edits to `zanac.asm`: group consecutive `DB` lines by their
address comment, filter >16 bytes, subtract KB `address` ranges.
