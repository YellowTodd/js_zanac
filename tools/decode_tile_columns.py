#!/usr/bin/env python3
"""Account for the tile-column / greeble data regions (sprint 0066).

The scroll engine (`scroll_map_reader` 0x98D4) walks a **column-descriptor
stream** whose entry pointer comes from a map-script column-group slot (cmd 2/4
byte3:4) or stream slot (cmd 5 / cmd B). The stream, from 0x98ED/0x9901, is a
linked structure of 3-byte records preceded by a count byte:

    [count]                         ; IY+7  number of column-runs
    then per run a 3-byte record [b0][lo][hi]:
      b0 == 0x00 : LINK  -> continue reading the stream at 0xHILO
      b0 == 0xFF : ADVANCE column by `count`, continue at 0xHILO - 1
      else       : COLUMN run of `b0` columns whose tile source = 0xHILO,
                   then the next byte is a new [count]

This walker follows every script's column pointers through that structure,
marking consumed bytes, and reports coverage of the two greeble regions.

Usage: .venv/bin/python tools/decode_tile_columns.py
"""
import sys
sys.path.insert(0, "tools")
import decode_mapscript2 as ms

ROM = ms.ROM
REGION1 = (0x9B64, 0xA443)
REGION2 = (0xB7A6, 0xBE26)
TILE_TABLES = (0xA444, 0xA653)
STRIP = (0xA654, 0xA65B)


def b(a):
    return ROM[a - 0x4000]


def w(a):
    return b(a) | (b(a + 1) << 8)


def in_regions(a):
    return REGION1[0] <= a <= REGION1[1] or REGION2[0] <= a <= REGION2[1]


def script_column_pointers():
    """Collect (script_idx, cmd, ptr) column-data pointers from all 9 scripts."""
    ptrs = []
    for idx in range(9):
        for (a, row, cmd, note, raw) in ms.parse(ms.SCRIPTS[idx]):
            nib = cmd & 0xF
            body = a + 3
            if nib in (2, 4):                    # 5-byte records: byte3:4 = ptr
                n = raw[0]
                for k in range(n):
                    rec = body + 1 + k * 5
                    ptrs.append((idx, cmd, w(rec + 3)))
            elif nib == 5:                        # stream slots: per rec ptr
                n = raw[0]
                q = body + 1
                for k in range(n):
                    b0 = b(q)
                    # record layout: byte0 slot, then (bit3 clear) 3 bytes incl
                    # a 2-byte ptr at q+2:q+3; (bit3 set) 4 bytes ptr at q+3:q+4
                    if b0 & 0x08:
                        ptrs.append((idx, cmd, w(q + 3)))
                        q += 5
                    else:
                        ptrs.append((idx, cmd, w(q + 2)))
                        q += 4
            elif nib == 0xB:                      # wide slot: ptr in E155 copy
                ptrs.append((idx, cmd, w(body + 2)))
    return ptrs


def walk_stream(entry, covered, seen):
    """Follow the column-descriptor stream from `entry`. cmd-2 stores the entry
    ptr into IY+2/3 and the engine's first advance does INC HL x3, so the real
    stream starts at entry+3. Records are 4-byte `[cnt][b0][lo][hi]`:
      b0==0x00 -> LINK, continue at 0xHILO (which is itself entry-3-style: the
                  engine EX DE,HL then reads count, no +3 skip on links)
      b0==0xFF -> ADVANCE, continue at 0xHILO-1
      else     -> COLUMN, tile source = 0xHILO -> walk_tile_source
    """
    # first advance skips 3 bytes (the entry's b0/lo/hi), then reads a count
    covered.add(entry); covered.add(entry + 1); covered.add(entry + 2)
    p = entry + 3
    guard = 0
    link = False
    while in_regions(p) and guard < 3000:
        guard += 1
        key = ("s", p)
        if key in seen:
            break
        seen.add(key)
        cnt = b(p)
        covered.add(p)
        b0 = b(p + 1)
        lo = b(p + 2)
        hi = b(p + 3)
        covered.add(p + 1); covered.add(p + 2); covered.add(p + 3)
        tgt = lo | (hi << 8)
        if b0 == 0x00:                            # LINK
            if not in_regions(tgt):
                break
            p = tgt
        elif b0 == 0xFF:                          # ADVANCE + jump
            if not in_regions(tgt - 1):
                break
            p = (tgt - 1) & 0xFFFF
        else:                                     # COLUMN
            if in_regions(tgt):
                walk_tile_source(tgt, covered, seen)
            p += 4


def walk_tile_source(src, covered, seen):
    """Tile-source record `[row][len][len tile bytes]` (0x9962: B=(HL), A=(HL+1),
    then LDIR of `len` bytes). Mark 2+len bytes; some are chained runs."""
    p = src
    n = 0
    while in_regions(p) and ("t", p) not in seen and n < 40:
        seen.add(("t", p))
        row = b(p)
        ln = b(p + 1)
        for k in range(2 + ln):
            if in_regions(p + k):
                covered.add(p + k)
        p += 2 + ln
        n += 1
        if ln == 0:                               # terminator record
            break


def main():
    ptrs = script_column_pointers()
    inreg = [pp for pp in ptrs if in_regions(pp[2])]
    intbl = [pp for pp in ptrs if TILE_TABLES[0] <= pp[2] <= TILE_TABLES[1]]
    print("script column pointers: %d total; %d -> greeble regions; %d -> "
          "tile_tables; %d elsewhere"
          % (len(ptrs), len(inreg), len(intbl),
             len(ptrs) - len(inreg) - len(intbl)))
    covered = set()
    seen = set()
    for (idx, cmd, ptr) in ptrs:
        if in_regions(ptr):
            walk_stream(ptr, covered, seen)
    for (name, lo, hi) in [("region1", *REGION1), ("region2", *REGION2)]:
        tot = hi - lo + 1
        hit = sum(1 for a in range(lo, hi + 1) if a in covered)
        print("%s 0x%04X-0x%04X: %d/%d = %.1f%% reached by column walk"
              % (name, lo, hi, hit, tot, 100.0 * hit / tot))


if __name__ == "__main__":
    main()
