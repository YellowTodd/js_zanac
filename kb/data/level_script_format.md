---
address: 0xA65C
end: 0xB7A5
kind: data
name: level_script_format
confidence: confirmed
sprint: "0056"
tags: [scroll, level-map, map-script]
---

> Address keyed to the map-script **data** region (0xA65C–0xB7A5). The master
> pointer table that indexes it lives at 0x945C (documented below).

# Level map-script format

Decoded sprint 0029. The MSX level engine uses a **row-triggered map-script**
stream, structurally identical to the NES version documented in
`xtra/nes-zanac-graphics.txt` (adopt that vocabulary: *map command*, *base
layer block*, *greeble*, *stop code*). The MSX format is one ROM bank, simpler
than the NES 8-greeble-layer system.

## Master script pointer table (0x945C)

9 little-endian words selected by `sub_9444` (0x9444): given the current scroll
position in HL, it walks the table from entry 7 down and returns the index of
the first entry the position is ≥. Stored to `stage_index` (0xE701). The scripts
themselves occupy ROM 0xA65C–0xB7A5.

| Idx | Ptr    | Idx | Ptr    | Idx | Ptr    |
|-----|--------|-----|--------|-----|--------|
| 0   | 0xB7A5 | 3   | 0xB1DE | 6   | 0xAAEF |
| 1   | 0xB61A | 4   | 0xAF1F | 7   | 0xA751 |
| 2   | 0xB3FD | 5   | 0xAD61 | 8   | 0xA65C |

(Pointers descend; entry 8 = 0xA65C is the lowest/first script, entry 0 =
0xB7A5 the highest. The observed live `stream_ptr` = 0xA7A0 lies inside the
0xA751 script.)

## Row-trigger model

The script is consumed as a forward-only stream (cached in `stream_ptr`
0xE704). The main scroll driver (`sub_94c3` 0x94C3 → `LAB_94d1` 0x94D1) works as:

Start-up detail (0x941B, worth stating because getting it wrong silently drops
every command on the script's first trigger row): `map_script_init` reads the
first 2-byte trigger into `next_cmd_row`, then seeds
**`level_row_ctr = trigger − 1`** (`DEC DE; LD (0xE702),DE` at 0x9424). The very
first `map_script_step` therefore increments the counter onto the trigger and
fires immediately. Seeding the counter at 0 instead skips it.

```
each frame:  level_row_ctr (0xE702)++
LAB_94d1:    if level_row_ctr != next_cmd_row (0xE706):
                 -> 0x97E3  build one tile row this frame, no command
             else:
                 read command at stream_ptr, dispatch (below)
                 after handler -> LAB_97d5: read next 2-byte row trigger,
                 store stream_ptr/next_cmd_row, loop to LAB_94d1
```

So multiple commands may fire on the same row; row triggers are **nondecreasing**
16-bit LE values, exactly like the NES "you can't edit the map in the past" rule.

## Command record

```
[row : 2 bytes LE]  [command : 1 byte]  [operands : variable]
```

The command byte is stored whole at `(IX+0x0F)` (high nibble = parameter for
some handlers), then `AND 0x0F` indexes the **inline jump table at 0x94EB** via
the `sub_5c2e` dispatcher (`CALL 0x5C2E` followed by a 13-entry word table).
Each handler ends with `JP 0x97D5` to fetch the next command. **All 13 handlers
disassembled and verified byte-identical sprint 0056** (they had been raw `DB`
code-in-DB blocks; the jump table is now labelled `map_cmd_jump_table`). Note
the parser runs with **IX = 0xE700** (scroll_state), so `IX+0x01` = stage/round
byte 0xE701, `IX+0x0F` = command byte, etc.

| Cmd | Handler | Role | Operands |
|-----|---------|------|----------|
| 0x0 | 0x97A8 | Set `spawn_ctrl` (0xE12D) from operand; if bit2 set, fall into cmd 1 placement | 1 (+ cmd1) |
| 0x1 | 0x97B3 | **Scripted enemy waves**: count N + N×3-byte records; each clear column gets an entity of type **0x45 (69)** carrying the record in +0x01/+0x02/+0x03 — see below | 1 + N×3 |
| 0x2 | 0x9505 | **Configure column-group slots** (base layer / greebles): count N + N×5-byte specs into 0xE2C0 | 1 + N×5 |
| 0x3 | 0x9537 | **Relocate a column group**: count N + N×2-byte `[src][dst]`; copies the 8-byte descriptor 0xE2C0+src*8 → 0xE2C0+dst*8 and disables the source (0x80) | 1 + N×2 |
| 0x4 | 0x956C | Column-group setup, **additive** (`(IY+0) += operand`) variant of cmd 2 | 1 + N×5 |
| 0x5 | 0x95A0 | `load_stream_slots(C=0)` (0x95A8) — activate inner tile-stream slots at 0xE2E0 | variable (greeble specs) |
| 0x6 | 0x9678 | Set byte 0xE71C from operand | 1 |
| 0x7 | 0x9680 | **Disable column-group slots**: count N + N slot indices → `(0xE2C0+slot*8)=0x80` | 1 + N |
| 0x8 | 0x9699 | **"ROUND n" banner** (intermission): store 2-byte operand→0xE720, set 0xE15E=0x96, set 0xE102 bit4, then print inline string `" ROUND "` (`round_banner_text`) + round digit `(IX+1)=0xE701+'0'` to name-table VRAM 0x3948 via `sub_5c25`/`sub_5bfc`. **Live-confirmed (print at 0x96BF fired once at round start, 0xE701=round).** | 2 |
| 0x9 | 0x96DE | **Round-script jump**: read 2-byte pointer → `JP sub_9433` (0x9433): resolve stage via `resolve_round_from_ptr`, store 0xE701, render round digit (`0x4C68`), then reload the script (`LAB_941b`) from the new pointer | 2 |
| 0xA | 0x96E5 | **Repaint the debris tiles**: operand is a colour byte → tiles 0x3A-0x3E verbatim, tiles 0xA7-0xAA as `glyph_col_data[i] \| (fill & 0x0F)`, all 8 rows, all 3 banks | 1 |
| 0xB | 0x9742 | **Special stream-slot config**: copy 4 operand bytes → 0xE155–0xE158, clear 0xE154, index `cmd11_index_table` (0x976C) by `0xE157 & 0x1F` → 0xE153, then init slot 0 via `init_stream_slot` (0x95C0) | ≥4 |
| 0xC | 0x977D | **Spawn-pace nudge** = the *scripted* ALC input ([[alc-adaptive-difficulty]] family 2): add signed operand to the spawn accumulators, set 0xE12D bit0. **Asymmetry (2026-07-30):** the handler branches on the operand's sign bit (0x9782). A **positive** operand raises only 0xE132 (saturating at 0xFF) and jumps straight to the bit0 set — 0xE12E is untouched. Only the **negative** path (0x978E) applies the delta to both, clamping each at 0. | 1 |

### Command 0x2 — column-group / base-layer specs (confirmed)

`02 N` then N records of 5 bytes each, written into column-group slot
`0xE2C0 + slot*8`:

```
byte0: slot index (0–15)
byte1: status / row-count
byte2: param byte (selects tile-block source via bits, see scroll_map_reader)
byte3: ptr lo  ┐ 16-bit pointer to tile-column data (typically 0xB9xx)
byte4: ptr hi  ┘
```

(Slot timers `(IY+6)` / `(IY+7)` are forced to 1 on load.) The outer loop of
`scroll_map_reader` (0x98D4) then consumes these slots one column per frame.

> **Slot-count correction (2026-07-30).** This paragraph said the reader
> consumes **16** slots. It consumes **4**: `LD B,0x4` at 0x98D2, with
> `LD DE,8 / ADD IY,DE` at 0x99C9, covering 0xE2C0–0xE2DF only. The 16 comes
> from `map_script_init`'s reset loop (0x9413: `LD DE,4 / LD B,0x10`), which
> stamps `0x80` every **4** bytes across 0xE2C0–0xE2FF — deliberately blanketing
> both the four 8-byte column-group slots *and* the eight 4-byte greeble stream
> slots at 0xE2E0 in one pass. Two different tables, one clearing loop.

## Commands 1, 3 and A decoded (2026-07-30)

These three were listed with their operand lengths but their *effects* were
only sketched. All three were re-read byte by byte for the web port.

### Command 1 (0x97B3) — scripted enemy waves

Not a tile placement. Each 3-byte record becomes an entity of type **0x45
(69)**, the invisible wave emitter [[base_spawner_active]]. The record lands in
the slot's +0x01/+0x02/+0x03, and the very first thing that handler does
(0x7A6D) is re-read them as **(enemy type, count, fire interval)** before
`random_x_pos` overwrites the position. So the record is:

| byte | meaning |
|------|---------|
| 0 | enemy type the emitter sends |
| 1 | how many to send |
| 2 | frames between them (0x28 in the table-driven type-11 variant) |

It is the same shape as [[base_spawner_spawn_table]], written inline in the
script instead of selected by the encounter counter. A blocked column
(`check_col_clear` returning carry) consumes its three bytes and places
nothing (0x97C4). **Command 0 falls into this same body** when its control
byte has bit 2 set (0x97AD), with the records following the control byte.

This is a major source of airborne enemies: wiring it up took a round-1 census
from 20 distinct entity types to 26.

### Command 3 (0x9537) — relocate a column group

Each 2-byte record is **`[src][dst]`**. The eight descriptor bytes at
`0xE2C0 + src*8` are copied to `0xE2C0 + dst*8`, and then **the source's status
byte is set to 0x80** (0x9552), disabling it. A greeble stream therefore
changes which column it feeds without restarting. The old "tile-data copy"
description had the mechanism right but not what was being copied.

The operand order is easy to read backwards, and getting it wrong disables the
wrong slot. 0x953F builds `DE` from the **first** operand byte and 0x954D
builds `HL` from the **second**; `EX DE,HL` at 0x954F then swaps them, so the
`LD A,(HL)` / `LD (DE),A` pair at 0x9550 reads the first slot and writes the
second, and `LD (HL),0x80` disables the first. (Ported backwards at first —
see correction 73 in [[port-corrections]] for what that looks like on screen.)

### Command A (0x96E5) — repaint the debris tiles

The operand is a **colour byte**, not a fill nibble, and the target is the
**colour table**, not a glyph blit:

- VRAM 0x21D0 = colour table entry for tile **0x3A**; `C = 5` covers tiles
  0x3A-0x3E — exactly the crater/rubble set the structure stamper (0x88ED) and
  the base-clear ceremony leave behind. They take the operand verbatim.
- VRAM 0x2538 = tile **0xA7**; `C = 4` covers 0xA7-0xAA, which take
  `glyph_col_data[i] | (operand & 0x0F)` from the 4-byte table at 0x973E
  (`00 00 70 50`).

Both writes fill all 8 rows of each tile and repeat for all three Screen-2
banks (0x9732 adds 0x800 per pass). The point is that wreckage always matches
the terrain it is lying on: round 1 issues `fill = 0x6C` at row 0 and
`0xE6` at row 2730.

## Worked example — script @0xA65C (first commands)

```
A65C: 00 00  06 55                  row 0:   cmd6  E71C=0x55
A662: 14 00  02 02 00 0A 55 AF B9   row 20:  cmd2  N=2:
                  01 17 55 D1 B9            slot0 {st=0A par=55 ptr=B9AF}
                                            slot1 {st=17 par=55 ptr=B9D1}
A670: 1E 00  08 ...                  row 30:  cmd8  (wide-struct ptr 0xA6EC)
...
```

Row triggers 0, 20, 30, … increase monotonically, confirming the model.

## Byte-exact operand lengths (sprint 0062)

All 13 handlers' operand consumption is now byte-exact — see
[[ground_structure_placement]] for the full table and derivation. Summary:
cmd 0 = 1 (+`1+3N` if operand bit2 set); 1 = `1+3N`; 2 = `1+5N`; 3 = `1+2N`;
4 = `1+5N`; 5 = `1+Σ(4 or 5 per record, +1 when record byte0 bit3 set)`;
6 = 1; 7 = `1+N`; 8 = 2; 9 = 2 (terminal); A = 1; B = 7; C = 1.
`tools/decode_mapscript2.py` walks **all 9 scripts + the warp stub** with
strictly non-decreasing rows and clean termination — the desync-free proof.
Commands 0/1/3/4/5/A/B are therefore **no longer opaque**.

### Script index → round & jump chain

Scripts descend by address; **round = 8 − table-index** (idx 8 @0xA65C = R0 …
idx 0 @0xB7A5 = R8). Each ends in cmd 9 except R8, which ends on a **`0xFFFF`
row trigger** at 0xB94C: `level_row_ctr` counts up from 0 and never reaches
0xFFFF, so the interpreter simply stops firing commands and the round runs on
into the ending — no terminator opcode is involved. The jump chain is:
`R1→R2→…→R7`, `R7→R7` (self-loop), `R0→R8`, `R8→ending`. Every cmd-9 target is
a real round entry — **no hidden sibling stub** in the mainline streams. The one
warp-only re-entry stub (0xAD4B, → round 0's invisible totem) lives *between*
scripts and is reached only via a warp orb ([[idol-warp-orbs]]).

## Live confirmation (sprint 0056, `tools/scroll_confirm.py`)

During real gameplay (round 1), with non-breaking probes:

- **Program-counter model holds.** `stream_ptr` (0xE704) walked strictly forward
  `0xA75B → 0xA760 → 0xA76C → 0xA77A` while `next_cmd_row` (0xE706) stepped
  `30 → 50 → 80 → 110` and `level_row_ctr` (0xE702) climbed monotonically toward
  each trigger — a command fires precisely when row == trigger, then a new
  2-byte trigger is loaded.
- **Commands 2, 5, 8 observed** dispatched at PC 0x94E8 (`A & 0xF`).
- **cmd 8 = ROUND banner**: print site 0x96BF fired exactly once at round start;
  `0xE701` read back as round number `1`.
- **Per-frame routines**: `scroll_vram_write` (0x9A79) ≈ 60 hits/s (every VBLANK);
  `scroll_map_reader` (0x9888) runs regularly under the row-trigger driver.

## Tool

`tools/decode_mapscript.py` parses the simple commands and prints the
row-trigger stream; complex commands are flagged for manual inspection.
`tools/scroll_confirm.py` (sprint 0056) live-confirms the interpreter and PC model.
