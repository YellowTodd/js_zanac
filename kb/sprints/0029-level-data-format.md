---
id: "0029"
status: done
range: 0xA444-0xA5C4,0xA7A0-0xBFCB
strategy: data_table
budget_turns: 25
---

# Sprint 0029 — Level data and stage progression

## Terminology (adopted from NES Zanac analysis — `xtra/nes-zanac-graphics.txt`)

The NES Zanac analysis by ManxomeBromide introduces a vocabulary that applies
well to the MSX version. Adopt these terms throughout:

| NES term | MSX equivalent | Notes |
|----------|---------------|-------|
| **Metatile** | 16×16 tile composed of 4 × 8×8 sub-tiles | MSX name tables use 8×8 tiles in Screen 2 |
| **Base layer block** | Repeating background tile row(s) | Selected by stage_index (0xE701) via tables at 0xA444 / 0xA4A4 / 0xA564 |
| **Greeble** | Individually placed tile decoration | In MSX: stream-slot entries managed by `load_stream_slots` (0x95A8) |
| **Map script** | Level data stream with row-indexed commands | In MSX: the compressed stream at 0xA7A0+ consumed by `scroll_map_reader` (0x9888) |
| **Stage** | One visual+music section of the level | MSX: 8 stages (0xE701 = 0–7); NES has 12 areas |

**Read `xtra/nes-zanac-graphics.txt`** before executing this sprint. The NES
format is more complex (bankswitched ROM, 8 greeble layers, 12-byte map commands)
but the architecture is the same: a streaming map script interpreted row by row,
a base-layer tile block system, and decoration greebles layered on top. The
MSX version is structurally simpler (one ROM bank, fewer layers).

## Goal

1. **Tile tables** — decode the three per-stage palette tables:
   - 0xA444 (primary tile IDs, 8 stages)
   - 0xA4A4 (tile variant A, 8 stages)
   - 0xA564 (tile variant B, 8 stages)
   Confirm how many bytes per entry, how each stage selects its visual theme.

2. **Map script format** — decode the stream format consumed by `scroll_map_reader`.
   The stream is at 0xA7A0+ (confirmed from 0xE704 live observations). Identify:
   - Row-trigger format (how many bytes per command, how the row counter maps)
   - Base-layer-block command (NES: Map Command 1)
   - Greeble placement command (NES: Map Commands 6/7)
   - Speed/throttle command (NES: Map Command 0)
   - Level-end / stage-transition command (NES: Map Command 5 = Stop Code)

3. **Stage boundaries** — how many map-script rows per stage? When does
   0xE701 increment? Where in the stream are stage boundaries?

4. **Entity spawn table** — the ground-structure entity type sequence at 0xBECC+
   (confirmed by `ground_struct_spawn_ctrl` sprint). Decode its format: is it
   a flat list of type bytes, or does it embed spawn parameters?

## Inputs

- `kb/data/scroll_state.md` — 0xE701 (stage_index), 0xE702 (level_row_ctr),
  0xE704 (stream_ptr, observed = 0xA7A0), 0xE714 (scroll_row, 23→0 wrap)
- `kb/symbols/0x9000-scroll/scroll_map_reader.md` — sub_9888: uses (0xE702) & 7
  as stage index into 0xA444/0xA4A4/0xA564 tables; outer/inner stream loops
- `kb/symbols/0x9000-scroll/ground_struct_spawn_ctrl.md` — spawn table pointer
  at 0xE133 (confirmed pointing to 0xBECF during gameplay)
- `xtra/nes-zanac-graphics.txt` — structural reference for terminology and
  comparable map-script architecture

## Verification plan

### Step 1 — Read tile tables (pure ROM)

```python
with ZanacGame.launch() as game:
    msx = game.client

    # Primary tile table (8 stages × N bytes)
    print("Tile table 0xA444:")
    data = bytes(msx.read_memory(0xA444, 96))
    for i in range(0, 96, 16):
        print(f"  {0xA444+i:04X}: {' '.join(f'{b:02X}' for b in data[i:i+16])}")

    # Variant tables
    for addr, label in [(0xA4A4, "Variant-A"), (0xA564, "Variant-B")]:
        d = bytes(msx.read_memory(addr, 96))
        print(f"\n{label} 0x{addr:04X}:")
        for i in range(0, 96, 16):
            print(f"  {addr+i:04X}: {' '.join(f'{b:02X}' for b in d[i:i+16])}")
```

Then determine entry size by looking for repeated patterns or known stage count.

### Step 2 — Map script stream decode

Start at 0xA7A0 and read the first 256 bytes. Attempt to parse as a series of
variable-length commands, looking for:
- 2-byte little-endian row trigger
- 1-byte command code
- Variable-length arguments

Cross-reference with `scroll_map_reader` source (lines 3997–4268) to understand
what the inner/outer stream loops consume.

### Step 3 — Stage-boundary watchpoint

```python
msx.cmd("set ::stage_changed 0")
wp = msx.cmd(
    "debug set_watchpoint write_mem 0xe701 {} "
    "{set ::stage_changed [reg PC]; set ::stage_row [debug read memory 0xe702]; "
    "debug break}"
)
msx.cont()
# Run until stage boundary fires or timeout
```

Record (stage_row, PC) when 0xE701 is written to confirm the boundary row and
which code advances the stage.

### Step 4 — Spawn table format

```python
# Read 64 bytes from the spawn table start at 0xBECC
data = bytes(msx.read_memory(0xBECC, 64))
print(' '.join(f'{b:02X}' for b in data))
# Also read current pointer from 0xE133
lo = msx.read_byte(0xE133); hi = msx.read_byte(0xE134)
ptr = (hi << 8) | lo
print(f"Current spawn_table_ptr: 0x{ptr:04X}")
```

## Focus questions

- How many bytes per tile-table entry? (Hypothesis: 1 byte per entry × 8 stages
  = 8 bytes per table, but 0xA4A4 − 0xA444 = 0x60 = 96 bytes ÷ 8 = 12 bytes/stage.)
- What format are the map-script greeble commands? Are they the same
  `load_stream_slots` (0x95A8) call arguments, or a different encoding?
- Is the entity spawn table truly a flat list of type bytes terminated by 0x00,
  or does it have headers/counts?

## Expected output

- New `kb/data/level_script_format.md` — map script command table (adopting NES
  terminology: base-layer-block command, greeble command, throttle command, etc.)
- `kb/data/tile_tables.md` — 3 tile palette tables with per-stage breakdown
- Updated `kb/data/scroll_state.md` with stage-boundary PC confirmed
- `kb/data/game_state_block.md` or scroll_state: stage count and row-per-stage

## Additional KB entries required (open-ref cleanup)

The ground-structure and encounter-counter routines at the end of ROM page 2
are called by already-documented symbols and must be added as symbol files.
All are static-only (no openMSX needed):

| Address | Caller | Purpose (hypothesis) |
|---------|--------|----------------------|
| 0xBE27 | `ground_struct_spawn_ctrl` | Spawn helper — loads ground-structure entity parameters |
| 0xBF94 | `ground_struct_spawn_ctrl` | Late-stage spawn branch — fallback slot allocation |
| 0xBFAB | `base_encounter_ctrl` / `handler_type35` | `inc_encounter_a`: increment counter at E12E (guarded by E150 bit 1) |
| 0xBFB3 | `base_encounter_ctrl` / `handler_type80` | `dec_encounter_a`: decrement counter at E12E; set E12D bit 0 |
| 0xBFBF | `base_encounter_ctrl` | `dec_encounter_b`: decrement counter at E130 |
| 0xBFC2 | `sub_bfa0` / `dec_encounter_a` | Inner: if (HL) != 0 decrement; else branch to bfd6 |
| 0xBFCB | `sub_bfa0` / `inc_encounter_a` | Inner: if E150 bit 1 clear, increment (HL); set E12D bit 0 |

The E12D/E12E/E130 encounter counters track how many active base-encounter
entities are present; E150 bit 1 is the "boss active" flag that gates spawning.

## Summary (filled at end)

Decoded the MSX level system, which mirrors the NES *map-script* architecture
(`xtra/nes-zanac-graphics.txt`): a row-triggered command stream, per-stage
base-layer tile blocks, and a scroll-position-driven entity spawn table.
Everything below is from static ROM analysis (the level tables and scripts live
in plain ROM 0xA444–0xBF2B; live reads would only re-confirm ROM bytes).

### 1. Tile tables (`kb/data/tile_tables.md`) — focus Q1 answered

Not 1-byte palette selectors and not 12 bytes/entry. Each entry is a **24-byte
vertical tile-column block** (24 = on-screen tile rows). Index math from
`sub_9888`:
- **0xA444** primary: 4 entries × 24, index `stage & 3`.
- **0xA4A4** variant A: 8 entries × 24, index `stage & 7`.
- **0xA564** variant B: 8 entries × 24, index `stage & 7` (ends 0xA623).

### 2. Map-script format (`kb/data/level_script_format.md`)

- **Master pointer table at 0x945C** — 9 LE words; `sub_9444` picks the stage by
  scroll position. Scripts occupy ROM **0xA65C–0xB7A5** (8 stages + entry).
- **Row-trigger model**: `level_row_ctr` (0xE702) +1/frame; when it equals
  `next_cmd_row` (0xE706) the command at `stream_ptr` (0xE704) runs. Triggers
  are nondecreasing — exactly the NES rule.
- **Command record**: `[row:2 LE][cmd:1][operands]`. `cmd & 0x0F` indexes the
  inline jump table at 0x94EB (via the `sub_5c2e` dispatcher). 13 commands
  (0x0–0xC) decoded and tabulated, including: cmd 2 = column-group/base-layer
  config (count + N×5), cmd 6 = set 0xE71C, cmd 7 = disable column groups,
  cmd 9 = **splice/jump to another script (advances the stage)**, cmd B = wide
  ground-structure config, cmd C = adjust scroll/encounter accumulators.
  Commands 0/1/3/4/5/A embed variable greeble/spawn sub-records.
- Verified by parsing the 0xA65C script: row triggers 0, 20, 30, 50, … rise
  monotonically; cmd 2 records decode to clean `{slot, status, param, ptr}`
  tuples. Tool: `tools/decode_mapscript.py`.

### 3. Stage boundaries — focus Q answered

`stage_index` (0xE701) is written at exactly two PCs: **0x403F** (level init) and
**0x9439** (`sub_9444`, reached only from the cmd-9 *splice* path
0x96DE→0x9433). So stages advance when the map script executes a splice command;
the script splices to the next stage's pointer (from the 0x945C table) and
`sub_9444` recomputes the stage number. No per-frame row counter advances it.

### 4. Spawn table (`kb/data/spawn_table.md`) — focus Q answered

A **flat list of entity-type bytes** at **0xBECC** (96 bytes, 0x00-terminated),
with no per-entry parameters — spawn position is a separate +8/entry
accumulator. `update_spawn_table_ptr` (0xBE27) re-points `spawn_table_ptr`
(0xE133 = 0xBECC + position offset) and selects a timer-reload value from the
0xBE76 table and a slice from the 0xBE7C pair table, all keyed by scroll
position.

### Open-ref cleanup (8 symbol files)

`update_spawn_table_ptr` (0xBE27), `spawn_type3d_slot` (0xBF94),
`inc_encounter_a` (0xBFAB), `dec_encounter_a` (0xBFB3), `dec_encounter_b`
(0xBFBF), `dec_encounter_inner` (0xBFC2), `inc_encounter_inner` (0xBFCB).
The encounter mutators adjust counters at 0xE12E/0xE130 (inc gated by the
boss-active flag 0xE150 bit 1), request a spawn recompute via 0xE12D bit 0, and
fall into the shared HUD-display tail at 0xBFD6. Pre-existing umbrella docs
(`sub_bfa0`, `base_encounter_ctrl`, `ground_struct_spawn_ctrl`) were re-scoped
to disjoint address ranges so the new granular entries don't overlap.

### Deliverables

- `kb/data/level_script_format.md`, `kb/data/tile_tables.md`,
  `kb/data/spawn_table.md` (new).
- 8 symbol files (open-ref cleanup) + re-scoped 3 existing docs.
- `kb/data/scroll_state.md` updated: 0xE701/0xE702/0xE704/0xE706 row-trigger
  semantics confirmed.
- `tools/decode_mapscript.py` (map-script parser).
- `zanackb validate`: **0 errors**; all targeted open-refs resolved; no new
  warnings from the new entries.

### Left open

- Byte-exact operand layout of the variable commands (0/1/3/4/5/A) — they embed
  greeble/spawn sub-records parsed by 0x97BC / 0x95A8 / 0x95C0 / 0x970A.
- `sub_9444`'s exact "position" input and how the descending pointer table maps
  to the 1–8 stage numbering.
