---
address: 0x9B64
end: 0xA443
kind: data
name: tile_column_data_region1
confidence: likely
sprint: "0066"
tags: [scroll, level-map, tile, greeble, data-block, d-scroll, e-level]
---

# tile_column_data_region1 (0x9B64–0xA443, 2272 B)

Region 1 of the two **tile-column / greeble** data blocks that bracket the map
scripts (region 2 = [[tile_column_data_region2]]). It holds the background
decoration and ground-structure tile patterns the scripts splice into the
scrolling map; it is referenced **by pointer** from map-script column-group
slots (cmd 2/4 byte3:4) and stream slots (cmd 5 / cmd B). See
[[level-data-block-map]] for the region carving and [[level_script_format]] for
the script side.

## Reader — `scroll_map_reader` (0x98D4)

Each active column-group slot (`IY = 0xE2C0 + slot*8`) keeps a cursor `IY+2:3`
into this data. When the per-column timers `IY+6/IY+7` expire the engine reads
the next **column-descriptor record** and, for a normal column, the referenced
**tile-source record**:

```
Column-descriptor record — 0x98F6/0x9901:
  [cnt]        -> IY+7  number of columns in this run
  [b0]         -> IY+6  per-column scroll width; also the record selector:
       b0 == 0x00 : LINK    (4 bytes) continue the stream at 0xHILO
       b0 == 0xFF : ADVANCE (2 bytes) column position += cnt, next record
                            starts at the byte right after b0
       else       : COLUMN  (4 bytes) tile source = 0xHILO
  [lo] [hi]    -> 16-bit pointer 0xHILO  (LINK and COLUMN only)
  (the entry pointer from cmd 2 points 3 bytes before the first record: the
   engine's first advance does INC HL x3 before reading a count.)

Tile-source record (2 + len bytes) — 0x9962:
  [row] [len] [len tile bytes]     ; LDIR'd into the row buffer with a tile
                                     offset; e.g. 00 01 6D = row 0, 1 tile 0x6D
```

### ADVANCE record length correction (2026-07-30)

This entry previously described **all three** record kinds as 4 bytes. ADVANCE
is 2 bytes. At 0x9909 the engine has just done `LD E,(HL); INC HL; LD D,(HL)`,
so `HL` sits on the *high* byte and `EX DE,HL` puts the pointer in HL. The
`0xFF` branch then does:

```
9911  LD A,(IY+7); ADD A,(IY+0); LD (IY+0),A   ; column += cnt
991A  EX DE,HL      ; HL = address of the "high" byte again
991B  DEC HL        ; HL = address of the "low" byte
991C  JR 0x98F6     ; re-enter the reader there
```

Re-entering at 0x98F6 reads that byte as the **next record's `cnt`** and the one
after it as the next `b0`. So the two bytes a 4-byte reading would treat as a
pointer are in fact the start of the following record, and the 16-bit pointer
loaded into DE is discarded. Reading ADVANCE as 4 bytes desynchronises the
column stream two bytes at a time.

Region 1 opens (0x9B64) with a run of `[00][01][tile]` tile-source records
(descending tile IDs `6D 6B 69 …`), matching the `cmd 1` placement-record shape.

## Verification (`tools/decode_tile_columns.py`)

Walking the column-descriptor structure from **all 9 scripts' column pointers**:
- **427 script pointers target this region** (41 distinct entry points, range
  0x9CB4–0xA42B) — confirming the wiring.
- Following the engine's exact 4-byte-record + tile-source logic reaches ~48% of
  the region's bytes directly; the remainder is contiguous tile-source pattern
  data of the same two record types, reached only through deeper `0x00`/`0xFF`
  link chains (notably a large packed sub-block 0x9EAB–0xA2BA). Every byte is a
  column-descriptor or tile-source record consumed by 0x98D4.

`confidence: likely` — the record formats and reader are disassembled and
quoted, and the pointer wiring is proven; a full byte-exact traversal of the
nested link graph is left open (the per-record field content is data, not
structure). See [[level-data-block-map]] "Left open".

## See also

[[tile_column_data_region2]], [[tile_tables]], [[level_script_format]],
[[level-data-block-map]], [[scroll_map_reader]], [[copy_tile_column]].
