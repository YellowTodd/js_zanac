---
name: ground_structure_placement
description: "Byte-exact operand grammar of all 13 Zanac map-script commands (jump table 0x94EB); lets tools/decode_mapscript2.py walk all 9 scripts + the warp re-entry stub without desync; covers cmd 12 (0x8C) scripted ALC pacing and the per-round idol table (0xE720) format/consumer."
kind: guide
confidence: confirmed
sprint: "0062"
tags: [map-script, scroll, level-map, ground-structure, idol, warp, alc]
---

# Ground-structure placement-stream format (byte-exact)

> Data range: map scripts **0xA65C–0xB94B** (interleaved with per-round idol
> tables); indexed by [[level_script_format]]'s pointer table @0x945C.

> Completes [[level_script_format]]: the **exact** operand length of every
> map-command handler, derived statically from the 13 handlers behind the jump
> table @0x94EB (all disassembled sprint 0056; consumption re-derived & verified
> sprint 0062). With these lengths `tools/decode_mapscript2.py` walks **all 9
> scripts + the warp re-entry stub start→end with strictly non-decreasing row
> triggers and clean termination** — the definitive desync-free proof of the
> grammar. Closes the format gap left by sprints 0060/0061.

## Stream record

Each map-script record is:

```
[row : 2 bytes LE]  [cmd : 1 byte]  [operands …]
```

The parser (`LAB_94d1` 0x94D1) fires a record when `level_row_ctr` (0xE702) ==
`next_cmd_row` (0xE706). The command byte is stored whole at `(IX+0x0F)`; only
its **low nibble** selects the handler (`AND 0x0F` @0x94E6), so `0x8C` and `0x0C`
both run handler 0xC. The **high nibble is a free tag**, unused by dispatch
(it *is* meaningful to a human reader — e.g. `0x8x` marks the "structural"
commands 8/9/A/B/C in the shipped data). Handlers end `JP 0x97D5`, which reads
the next `[row:2]` and leaves the pointer at the next cmd byte. Parser runs with
**IX = 0xE700** (`scroll_state`).

## Byte-exact operand lengths

`HL` enters a handler pointing at the **first operand byte** (after the cmd
byte). "len" below = operand bytes consumed (add 3 for the full record: 2 row +
1 cmd).

| Cmd | Handler | len (operands) | Meaning |
|-----|---------|----------------|---------|
| 0 | 0x97A8 | **1**, **+ cmd-1 body if operand bit2 set** | `E12D = op` (`spawn_ctrl`); if `op & 0x04`, falls into 0x97B3 → also consumes `1 + 3·N` placement bytes |
| 1 | 0x97B3 | **1 + 3·N** | `N` **3-byte tile-placement records**; each `CALL 0x97BC`: if column clear (`check_col_clear` 0x9B22) write tile 0x45 + copy the 3 bytes to the column buffer; the 3 bytes are consumed **whether or not** placed |
| 2 | 0x9505 | **1 + 5·N** | `N` 5-byte column-group slot specs → `0xE2C0 + slot·8` (base layer / greebles) |
| 3 | 0x9537 | **1 + 2·N** | `N` 2-byte `(src,dst)` records; relocates 7 tile bytes between `0xE2xx` slots (LDI×7 on RAM, **not** the stream), source marked 0x80 |
| 4 | 0x956C | **1 + 5·N** | like cmd 2 but **additive** on byte1 (`(IY+0) += op`) |
| 5 | 0x95A0 | **1 + Σ per-record** | `N` inner tile-stream slots → `0xE2E0`. **Per record: 4 bytes, or 5 if the record's byte0 bit3 is set** (bit3 → extra `(IY+1)` byte, `SET 6`). This is the only variable-per-record command. |
| 6 | 0x9678 | **1** | `E71C = op` |
| 7 | 0x9680 | **1 + N** | `N` slot indices → `(0xE2C0+slot·8) = 0x80` (disable) |
| 8 | 0x9699 | **2** | 2-byte ptr → **`0xE720` = per-round idol table** (`idol_table_ptr`); also raises the **"ROUND n" banner** (0xE102 bit4, prints `round_banner_text`) |
| 9 | 0x96DE | **2** (terminal) | 2-byte ptr → `JP 0x9433` (`resolve_round_from_ptr` + reload script). Ends the current stream. |
| A | 0x96E5 | **1** | `(IX+0x23) = op` fill nibble; blit a VRAM glyph cell |
| B | 0x9742 | **7** | copy 4 bytes → `0xE155…0xE158`; index `cmd11_index_table` (0x976C); then `init_stream_slot` (0x95C0) consumes **3 more** (E=0 ⇒ bit3-clear path) → 4 + 3 = 7 |
| C | 0x977D | **1** | **spawn-pace nudge** (see below) — this is the shipped **`0x8C` "cmd 12"** |

### cmd 5 — the variable-length one (worked)

`init_stream_slot` (0x95C0) advances the stream pointer by **3** when the
record byte0's bit3 is clear, and by **4** when set (an extra `(IY+1)` data
byte after `SET 6,(IY+0)`); the record's leading slot byte adds 1 ⇒ 4 or 5
bytes total. Both variants occur in the shipped data (112 four-byte + 213
five-byte records across the 9 scripts), so the branch is genuinely exercised —
and every script still terminates exactly on its jump/idol-table boundary,
proving the length rule.

## cmd 12 (`0x8C`) — the second ALC input

`0x8C nn` runs handler 0xC (0x977D) with **one signed operand `nn`**:

- `nn ≥ 0`: `E132 += nn` (saturating high at 0xFF).
- `nn < 0` (bit7): `E132 += nn` (saturating low at 0x00) **and** `E12E += nn`.
- Always: `SET 0,(E12D)`.

`0xE132`/`0xE12E` are the **spawn accumulators** that drive the spawn-pointer
advance (`0xE12F/0xE131`, [[alc-adaptive-difficulty]]). So each round's script
**injects difficulty pacing at specific rows** — a *second, scripted* ALC input
alongside the dynamic firing-cadence path (`shot_rate_table`). Round preambles
carry it (e.g. round 6 `0xAAF3: 8C 20` = `+0x20`). Same accumulators as the
runtime `spawn_pace_nudge` helpers (`0xBFAB` family). → feed to sprint 0067.

## Per-round idol table (`0xE720`) format & consumer

cmd 8 stores a per-round pointer into `0xE720` (`idol_table_ptr`). A ground
structure (idol/totem) entity reads it at **spawn init 0x87B0** (census bp
0x87C3):

```
0x87B0  C = (IX+0x03)            ; idol's byte offset into the table
0x87B6  HL = (0xE720) + C        ; NB: + C, not C·2  → table is a packed
0x87BA  (IX+0x1C) = table[C]     ;      byte-addressed pointer array
0x87BF  (IX+0x1D) = table[C+1]   ; +0x1C/1D = warp-destination pointer
0x87C3  (IX+0x03) = 0x24         ; cursor CONSUMED then reset to a fixed 0x24
0x87F6  render digit (IX+0x1C)+0x30 on the idol face
```

So `(IX+0x1C/0x1D)` is the 16-bit **warp destination** (→
`resolve_round_from_ptr` on orb-touch, [[idol-warp-orbs]]), and `(IX+0x1C)+'0'`
is the digit drawn on the idol. The nine per-round tables are:

| Round | idol table | (from script idx, round = 8 − idx) |
|-------|-----------|-------------------------------------|
| R0 | 0xA6EC | idx 8 @0xA65C |
| R1 | 0xAA68 | idx 7 @0xA751 |
| R2 | 0xAD33 | idx 6 @0xAAEF |
| R3 | 0xAF09 | idx 5 @0xAD61 |
| R4 | 0xB1BF | idx 4 @0xAF1F |
| R5 | 0xB3F5 | idx 3 @0xB1DE |
| R6 | 0xB604 | idx 2 @0xB3FD |
| R7 | 0xB787 | idx 1 @0xB61A |
| R8 | 0xB94C | idx 0 @0xB7A5 |

**All nine match the live census** (`sprint0060_census.py`, [[idol-warp-orbs]]
"E720 table" column) exactly — the static↔live cross-check for the idol binding.

### `(IX+0x03)` is a *dynamic cursor*, not a placement field

The probe (2026-07-04) saw the *same* placement record spawn `+0x03` = 0, 28,
88 across runs. Confirmed here: `+0x03` is the table **byte offset**, consumed
at 0x87B0 and immediately reset to `0x24`. It is assigned when the idol **entity
is allocated** (as the scroll reveals a ground structure), from a running
per-round cursor — **not** stored literally in the map-script record. Deriving
each idol's `+0x03`/type/`+0x18` purely statically therefore requires modelling
that allocation cursor (the tile-column → entity path around
`ground_struct_spawn_ctrl` 0xBF2C); the live census remains the authority for
per-idol destinations. This is the one residual data gap (structure, not format).

## Script chain & termination (all verified)

Scripts are stored descending by address; round = 8 − table-index. Every script
ends in cmd 9 except **R8 (idx 0 @0xB7A5)**, whose stream runs to ~0xB942 and
flows straight into the ending (no jump; parser stops at its idol-table
boundary 0xB94C). Chain, all cmd-9 targets = real round entries (⇒ **no hidden
sibling stub** in the mainline streams):

```
R1→R2→R3→R4→R5→R6→R7,  R7→R7 (self-loop),  R0→R8,  R8→ending
```

## Warp re-entry stub (0xAD4B–0xAD60) — verified

The warp-only stub (reachable solely via round 2's idx-4 orb, dest 0xAD4B;
[[idol-warp-orbs]]) decodes cleanly under this grammar:

```
0xAD4B row=0    cmd 6  E71C=0x33
0xAD4F row=50   cmd 8  idol_tbl = 0xAD31   (= normal 0xAD33 shifted −2)
0xAD54 row=50   cmd 5  N=1  (one 4-byte slot record)
0xAD5C row=50   cmd 9  → 0xAAEF            (replay round 2 from its start)
```

Because cmd 8 sets `0xE720 = 0xAD31`, the secret totem's `+0x03 = 0` reads
`table[0] = 5C A6 = 0xA65C` = **round 0's stream start** — the invisible-totem
gateway to round 0. One record later the replayed round-2 preamble's own cmd 8
(0xAAF9) restores 0xAD33.

## Tool

`tools/decode_mapscript2.py`:
- (no args) — pointer table + full decode of all 9 scripts, with per-script
  record count and end address;
- `0xNNNN` — decode one stream (also works on the stub @0xAD4B);
- `--struct` — per-round dump of placement/idol-table records.

Supersedes the heuristic `tools/decode_mapscript.py` (which flagged the variable
commands as opaque hex blobs).
