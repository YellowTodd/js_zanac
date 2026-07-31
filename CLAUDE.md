# Zanac RE — session instructions

The main disassebly is only `source/zanac.asm`, the other ASM files are checkpoint versions. Note that each ASM line has its absolute address (after loading in memory) marked in the start of its comment. Note that tabs have width 8 and DB lines define at most 16 bytes: you must keep the code correctly indented after edits.

Never load a ASM file in bulk. Always read bounded ranges with `Read` (offset + limit).

Do not commit, the user will do it.

## Subsystem map & coverage

The game is split into 15 subsystems, each with a detailed overview in
`kb/subsystems/<letter>-<slug>.md`. Work proceeds as documentation slices per
subsystem; the overview files list the member symbols, data, guides, sprints, and
open gaps. Coverage below is a **rough** estimate (documented + confidence-weighted
vs. estimated total scope), refreshed when a slice lands.

| Sub | Subsystem | Coverage | Notes / biggest gap |
|-----|-----------|----------|---------------------|
| A | Boot & hardware init | **done ✓** | fully documented (0040); all A routines live-confirmed, embedded code disassembled |
| B | Frame / render pipeline | **done ✓** | fully documented (0043); all routines live-confirmed, SAT-DMA split out (`sat_dma_to_vram`) |
| C | Entity framework | **done ✓** | fully documented (0044); dispatcher/collision/update live-confirmed, `death_transition_table` (0x716B) KB'd + DB'd |
| D | Scroll & tile rendering | **done ✓** | fully documented (0056); the engine is a **row-triggered map-script interpreter** (`map_script_step` 0x94C3, 13-cmd table @0x94EB; PC=0xE704/row=0xE702/trigger=0xE706, live-confirmed); cmd 8 = "ROUND n" banner, cmd 9 = round-script jump; DB blocks 0x9537/0x9678 disassembled; 0xE702 is the row counter (not stage index) |
| E | Level data & decompression | **done ✓** | fully documented (0037); custom-RLE decompressor + leaf helpers (`decompress_unit` 0x5D1A, `vdp_write_byte` 0x5C07) decoded; 0x9B64–0xBE27 carved into named sub-regions (`level-data-block-map`): tile-column/greeble data (regions 1+2), `tile_tables` (0xA444–0xA653, +0xA624/0xA63C fixed cols), 9 map scripts (0xA65C–0xB7A5 via ptr table 0x945C), `spawn_table`; inline VRAM string-print family (0x5C10/1F/25/28) split out |
| F | Player ship & weapons | **done ✓** | fully documented (0048); fire engine (switcher/timer/3-phase dispatch), ship handler, shot system + `set_velocity_from_dir` (0x4cf7) all live-confirmed |
| G | Enemy & spawn system | **done ✓** | fully documented (0049–0052: all enemy type-handlers types 4–89 live-confirmed; 0039 closed; DB blocks 0x8983/0x8a5a disassembled; type 72 = base core sets round flag e102 bit5, 73–79 = base segments) |
| H | Items & pickups | **done ✓** | fully documented (0054); box drop-table (type 4→bullets/5→nothing/6→chip), power chip = type 63 (`handler_type63_power_chip`, shot_level++), fire upgrade = black shadow (type 83 → `fire_select(+0x1c)`) — all live-confirmed |
| I | ALC (adaptive difficulty) | **done ✓** | fully documented (0055+0067); **no level byte** — **two input families** feed spawn accumulators E12E/F/E131/E132: (1) player firing (E13F→`shot_rate_table`, `player_ship_update` 0x7674 live-confirmed; base path `handler_type35` 0x8446) and (2) map-script cmd 12 spawn-pace nudge + cmd 8/9 round resets (0062/0067); 0x4B2A is *not* ALC (= `structure_award_index_table`) |
| J | Title screen | **done ✓** | fully documented (0041); all routines confirmed, `check_start_key`→`check_esc_key` (ESC live-confirmed) |
| K | Game-flow state machine | **done ✓** | fully documented (0045); E102 map + round progression confirmed (round=E701, `resolve_round_from_ptr`, no 2nd loop) |
| L | Ending & credits | **done ✓** | fully documented (0046); credits_display + init_credits_stream live-confirmed (screenshot), `compare_save_hiscore` KB'd |
| M | Secrets & warps | **done ✓** | fully documented (0058+0059, live-confirmed); (1) ESC-continue retains E701 (`check_esc_key`→`title_screen_init`), round 0 = a **real playable stage** (stream 0xA65C) whose tail is the ending; (2) **in-game warp orbs** (`idol-warp-orbs` guide): shoot idol (`handler_type70_wide_structure`) → type-72 **orb** (`handler_type72_base_core`), yellow=kill-all, **black=warp** via `+0x1C/1D` (from per-round idol table 0xE720, set by map-script cmd 8) → `resolve_round_from_ptr`; warp totems (entity **type 71** "smiling totem", census 0060) in rounds 1/2/5/7, **R2→R1 & R5→R4 go backward**, round 7 **loops** (self/R8); **round 0** via round-2 **type-70 "invisible totem"** (0xA356→R0, 0061); type-82 = fire-powerup box (digit=fire#, not a totem); **no hidden key combos**; `scripts/warp.tcl` = debug entry |
| N | HUD & status display | **done ✓** | fully documented (0047); all render routines live-confirmed; 0x4AEA = `score_award_table` (not glyphs) |
| O | Sound system | **done ✓** | fully documented (0057); PSG engine (0020) + track command format (0028) + **all 27 events catalogued & live-confirmed**: round-start BGM = ev7 (or ev2 on rounds ≡0 mod8) → chains to ev1 (main theme); shot SFX = `3+(E10F>>2)` (0x7234, pitch by shot state); music=1–5/7–12/25–27, SFX=6/13–24, explosion=ev18, chaining `0x87` (ev7→1, 12→5); `stop_all_sound` (0x516C; renamed 0068 from the misnomer `reset_enemies_and_psg`) confirmed = stop-all-sound (PSG-only) |

Excluded from scoring: the MSX BIOS thunks (`kb/symbols/0x0000-bios/`) and
sysvars (`0xF380-sysvars/`) — platform reference, not Zanac subsystems.

**Open sprints → owning slice** (close the sprint as the slice develops; each
open sprint carries a `subsystems:` field and a slice note):

- ~~0062~~ (**done 2026-07-05**: byte-exact map-command grammar — all 13 handlers' operand lengths (`tools/decode_mapscript2.py` walks all 9 scripts + the warp stub desync-free); `kb/guides/ground_structure_placement.md`. cmd 12 (0x8C) = scripted ALC spawn-pace nudge → E132/E12E; idol table (0xE720) = packed byte-addressed pointer array, `+0x03` = dynamic allocation **cursor** (not a static field), consumed at 0x87B0 → warp dest `+0x1C/1D`; all 9 idol-table ptrs + full round-jump chain match the live census; re-entry stub 0xAD4B decode confirmed, no sibling stub. **Residual → 0065**: static per-idol `+0x03`/type/`+0x18` attribution needs the tile-column→entity allocation cursor. ALC rewrite → 0067.)

**Completion plan** (goal: 100% — meaning of every code/data byte understood; run in order):

- ~~0063~~ (**done 2026-07-05**: `tools/coverage_audit.py` → 81.5% known, 7 unknown ranges all owned by 0062/0064–0066; found `data_4b2a`'s reader — code-in-DB @0x4A6A `add_score_for_subtype` → it's the `structure_award_index_table`; see `kb/guides/coverage-audit.md`)
- ~~0064~~ (**done 2026-07-05**: `tools/decode_tracks.py` walks all 27 events / 51 voices → **0x5236–0x5A10 100% byte-covered, 0 unknown opcodes**; cmd jump table @0x4F6C, operand lengths pinned; engine tables + 7 IDX_TRANSPOSE tables + `FF FF` tail all accounted; ev7→ev1 / ev12→ev5 chains; ev3 title music live-matched exactly. Region end corrected: 0x5A11=code. `kb/data/sound_track_scores.md`. Audit known% 81.5→87.66.)
- ~~0065~~ (**done 2026-07-05**: four orphan tables decoded, all **live-confirmed** in a round-1 base fight (invincible ship via `ZanacGame.make_invincible`; base encounter = scroll 0xE702 stalls). `data_4b2a`=[[structure_award_index_table]] (sub→idx matches ROM); 0x93AB=[[base_attack_patterns]] (8 ptrs→3-byte `(rate0,rateM,rate3)` records, `0x00`-loop; interp 0x8BF5, reader 0x8FDE round-robin via E717 — 21 in-range descriptor reads live); 0x9302=[[base_clear_award_index_table]] (indexed by `(E157)&1F`→`add_score` when base segment count E152→0; loaded idx 0x0A = ROM[0x9302+0], live MATCH); 0x51F0=[[psg_period_base_table]] (12 chromatic base periods→0xF200). [[dir8_delta_table]] zero reads over 45s play (dead, `likely`). Audit 87.66→87.96%.)
- ~~0066~~ (**done 2026-07-05**: **audit now 100.00% KNOWN, 0 unknown bytes.** Graphics 0x5D2C–0x70B8 fully tiled by `gfx_*` entries (no gaps, visual-confirmed via `zanac_shot`); tile-column/greeble regions decoded — `scroll_map_reader` (0x98D4) reads 4-byte column records `[cnt][b0][lo][hi]` (b0=00 LINK / FF ADVANCE / else COLUMN→tile-source `[row][len][tiles]`); `tools/decode_tile_columns.py` proves 467 script pointers land in-region. New: [[tile_column_data_region1]]/[[tile_column_data_region2]]/[[tile_strip_a654]]. Audit 87.96→100%.)
- ~~0067~~ (**done 2026-07-05**: ALC rewritten as **two input families** — (1) player firing [0055], (2) map-script cmd 12 spawn-pace nudge + cmd 8/9 round resets [0062] — in [[I-alc-adaptive-difficulty]]/[[alc-adaptive-difficulty]], cross-linked with [[level_script_format]]. **Confidence: 0 hypothesis** (place_tile_group/init_stream_slot/load_stream_slots → confirmed via 0062 grammar + 0065 live base; explode_enemies → confirmed live on base clear (enemies→0x23); `player_bullet_table` retired = it was the PSG sound-slot table @0xE20C misID'd in 2018). 359 confirmed / 34 likely (accepted w/ reasons) / 0 hypothesis.)
- ~~0068~~ (**done 2026-07-06**: **naming-consistency pass — asm labels now mirror KB names, provably byte-neutral** (`redisasm.py verify` after every batch). `tools/naming_audit.py` (gate: **0 (a)/(b)/residual**) + `tools/rename_symbol.py --from-kb` (address-keyed: 82 renamed / 62 inserted / 6 `DB`-split / 518+ refs — updates def **+ symbolic `JR`/`DJNZ` operands** + `-> ` arrows, re-aligning col-64 comments). `base_segment_table`(0x8DF1) recarved from mis-decoded code via `redisasm data`, resyncing `handler_type80_base_damage`(0x8E14). Misnomer `reset_enemies_and_psg`→[[stop_all_sound]] (0x516C, `aka` kept, 11 files); `handler_type72_base_core` **kept** (0059 was behaviour, not name). Guide `kb/guides/naming-conventions.md`; `redisasm` KB_LABELS is stale legacy, not used.) → all

(0060 closed — per-round **totem census** via live capture: warp totems = entity
**type 71** ("smiling totem", screenshot-confirmed); round 7 loops; catalogue in
[[idol-warp-orbs]]. The byte-exact placement-stream record format is left as a
minor data gap.
0061 closed — destruction sub-type map (0x880D): only `+0x18<0x51` spawns the
orb; type 82 = **fire-powerup box** (digit = fire#, not a totem), the `0x88A2`
`R&7` path is a **random fire type** not a warp; **round 0** reached in-game via
round-2's type-70 "invisible totem" (0xA356→R0), live-confirmed.)

(0036 closed by 0058 — all five HUD-misc routines had already landed via the N/K/F
slices: 0x4C74=[[render_hex_byte]] + 0x4AEA=`score_award_table` (N/0047),
0x4ACE=[[compare_save_hiscore]] (0046), 0x4C91=[[player_pos_snapshot]] (0044),
0x4CF7=[[set_velocity_from_dir]] (0048), 0x4E0B documented inside [[pause_handler]]
(0032); no residual N work.
0037 closed by the E slice — decompressor internals `vdp_write_byte`/
`decompress_unit`, string-print family, and `level-data-block-map`.
0038 closed by 0048 — its 0x730B fire branch is [[fire_life_timer]]; the
0x71DB/0x71F6 helpers remain G/C items. 0039 closed by 0049/0051 —
`LAB_7A67`=[[base_spawner_active]], `LAB_816D`=[[fire_ground_projectile]].)

## Unmapped / large DB regions

Large `DB` blocks (>16 bytes) in `source/zanac.asm` that are still unmapped —
either undisassembled code or unknown game data. Full per-block detail (purpose,
neighbours, patch commands) lives in `kb/guides/db-sections-with-code.md`. The
big unknowns, by size:

| Region | Bytes | Likely owner | Status |
|--------|-------|--------------|--------|
| ~~0x9B64–0xBE27~~ | ~8899 | E — round map / scroll stream data | **MAPPED ✓ (0037)** — carved into named sub-regions by `level-data-block-map`: tile-column/greeble data (0x9B64–0xA443, 0xB7A6–0xBE26), `tile_tables` (0xA444–0xA653), 9 map scripts (0xA65C–0xB7A5), `spawn_table` (0xBE76). Only per-round greeble-record field semantics left (data, not structure). |
| ~~0x5236–0x5A10~~ | ~2011 | O — music / SFX track data | **DECODED ✓ (0064)** — 100% byte-covered, 0 unknown opcodes; all 27 events / 51 voices walked (`decode_tracks.py`), per-track scores in `sound_track_scores`. (0057 catalogued events; 0064 proved byte-exactness. 0x5A11 = code, not data.) |
| ~~0x4B2A–0x4B82~~ | 89 | N — `data_4b2a` | **MAPPED ✓ (0063)** — it's the `structure_award_index_table`: score-award indices by destruction sub-type, read by `add_score_for_subtype` (0x4A6A, was code-in-DB — the "missing reader"). Live verify → 0065. |
| ~~0x93AB–0x93E3~~ | 57 | **G** — base-attack pattern table | **DECODED ✓ (0065)** — [[base_attack_patterns]]: 8 ptrs + 3-byte `(rate0,rateM,rate3)` records (`0x00`-loop), interp 0x8BF5, reader 0x8FDE via E717 |

**Coverage is measured by `tools/coverage_audit.py` (0063) — now 100.00% known,
0 unknown bytes** (completion gate met, sprint 0066). The greeble/tile-column
regions were the last unknowns → [[tile_column_data_region1]]/`region2`/
`tile_strip_a654` (0066). Numbers + retired-range table in
`kb/guides/coverage-audit.md`. Confidence debt: 0 `hypothesis`, all remaining
`likely` accepted with reasons (0067).

Mapped large DB blocks (graphics assets 0x5D2C–0x70B7, `spawn_table`,
`entity_jump_table`, credits script 0x4775–0x4897, etc.) and all patched
code-in-DB blocks are tracked in `db-sections-with-code.md`.

## Executing a sprint

1. **Read the sprint file**: `kb/sprints/NNNN-slug.md` — goal, inputs, verification plan.
2. **Read only the referenced KB inputs**: the sprint lists them explicitly.
3. **Run the verification**: all scripts go in `tools/`. Use `.venv/bin/python tools/scriptname.py`.
4. **Update KB**: create/edit files under `kb/symbols/`, `kb/data/`, or `kb/guides/`. Follow the frontmatter schema in `kb/guides/conventions.md`.
5. **Validate**: `.venv/bin/zanackb validate` — fix errors before marking done.
6. **Write the summary**: fill `## Summary (filled at end)` in the sprint file; flip `status: done`.

## Documentation protocol

KB files use YAML frontmatter + Markdown. Required fields for every symbol/data entry:
`address`, `kind`, `name`, `confidence`, `sprint`. See `kb/guides/conventions.md` for the full schema and the confidence ladder (confirmed / likely / hypothesis / guess).

File placement: `kb/symbols/0xNNNN-area/name.md` for routines and data, `kb/data/name.md` for large structures, `kb/guides/name.md` for cross-cutting references.

## openMSX automation

Reference: `kb/guides/openmsx-control.md`.

Key patterns:

```python
from zanackb.zanac_game import ZanacGame, MSXKey

with ZanacGame.launch("source/zanac.rom") as game:
    msx = game.client
    game.wait_for_title()
    game.start_game()        # holds SPACE until game is active

    # Read RAM / ROM
    data = bytes(msx.read_memory(0xE300, 32))   # hex-safe binary read
    val  = msx.read_byte(0xE14B)

    # Write RAM
    msx.write_byte(0xE150, 0x01)
    msx.write_memory(0xE780, bytes([0x60, 0x78, 0x44]))

    # Breakpoint: fires TCL action when CPU hits address
    msx.cmd("set ::hit 0")
    bp = msx.set_breakpoint(0x445F,
        "incr ::hit; if {$::hit % 10 == 0} {debug break}")
    msx.cont()
    time.sleep(0.4)          # CPU pauses on every 10th dispatch call
    raw = bytes(msx.read_memory(0xE300, 26*32))
    msx.remove_breakpoint(bp)

    # Write watchpoint (catches who writes an address)
    wp = msx.cmd("debug set_watchpoint write_mem 0xe71e {} "
                 "{set ::writer [reg PC]; debug break}")
    msx.cont(); time.sleep(2.0)
    pc = int(msx.cmd("set ::writer"), 16) if msx.cmd("set ::writer") != "0" else 0
    msx.remove_watchpoint(wp)

    # Keyboard injection
    game.steer(up=True)
    game.shoot_shot()        # hold SHIFT
    msx.key_press(*MSXKey.ZANAC_FIRE, duration=0.1)  # tap Z
```

**ROM reads** (works without gameplay): `msx.read_memory(0x8094, 32)` reads ROM page 2 directly after `ZanacGame.launch()` (BIOS maps cart automatically).

**PNG screenshots** (visual verification of background/sprites/logo): the normal
`ZanacGame.launch()` uses `-control stdio` → `renderer=none` → `screenshot`
fails. Instead use `tools/zanac_shot.py`, which launches openMSX with the SDL
renderer on `$DISPLAY` and connects via the auto-created control socket. View
the PNG with the `Read` tool. Full notes: `kb/guides/openmsx-control.md` §11.

```python
from zanac_shot import ShotSession            # tools/ on sys.path
with ShotSession(savestate="savestates/game-end.oms") as s:
    s.run(3.0); s.shot("/tmp/frame.png")      # then Read /tmp/frame.png
```

## Disassembling DB sections

Use `tools/redisasm.py` for DB blocks that contain code. Protocol in `kb/guides/redisasm-protocol.md`. Short form:

```bash
.venv/bin/python tools/redisasm.py checkpoint          # once per session

# Replace a DB block with disassembled instructions
.venv/bin/python tools/redisasm.py patch \
    --before "ANCHOR_REGEX_BEFORE_BLOCK" \
    --after  "ANCHOR_REGEX_AFTER_BLOCK"  \
    --start  0xADDR   --end 0xADDR        # exclusive end

# Insert a label before an already-decoded instruction (no openMSX needed)
# Primary form — locates the line by its ROM address comment:
.venv/bin/python tools/redisasm.py add-label --addr 0xADDR
# Override — use an explicit regex when the address comment isn't present:
.venv/bin/python tools/redisasm.py add-label \
    --addr   0xADDR \
    --before "REGEX_MATCHING_FIRST_INSTRUCTION" \
    --after  "REGEX_NARROWING_SEARCH_WINDOW"    # optional

.venv/bin/python tools/redisasm.py verify              # confirms ROM identity
```
