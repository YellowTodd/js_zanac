#!/usr/bin/env python3
"""Byte-exact Zanac map-script decoder (sprint 0062).

Walks a map-script stream start->end with the *exact* operand lengths derived
from the 13 command handlers (jump table @0x94EB), so all 9 scripts parse
without desync. Each stream record is:

    [row : 2 bytes LE]  [cmd : 1 byte]  [operands ...]

The command byte's low nibble selects the handler; the high nibble is a free
parameter stored at (IX+0x0F) but is *not* used for dispatch (so 0x8C and 0x0C
both run handler 0xC). Exact operand consumption per handler (HL enters a
handler pointing at the first operand byte, after the cmd byte):

    0 97a8  1  (+ cmd1 body when operand bit2 set: falls through to 0x97b3)
    1 97b3  1 + 3N          N 3-byte tile-placement records (tile 0x45 + rec)
    2 9505  1 + 5N          N 5-byte column-group slot specs  -> 0xE2C0+slot*8
    3 9537  1 + 2N          N 2-byte (dst,src) slot tile-copy records
    4 956c  1 + 5N          like cmd2, additive on byte1
    5 95a0  1 + sum(rec)    per rec: 4 bytes, or 5 if rec byte0 bit3 set
    6 9678  1
    7 9680  1 + N           N slot indices to disable
    8 9699  2               ptr -> 0xE720 (per-round idol table) + ROUND banner
    9 96de  2               ptr; JP 0x9433 reloads script (terminal for stream)
    A 96e5  1
    B 9742  7               4 bytes ->0xE155..; + 95c0 consumes 3 (E=0,bit3 clr)
    C 977d  1               signed spawn-pace nudge -> 0xE132/0xE12E (ALC cmd 12)

Usage:
    .venv/bin/python tools/decode_mapscript2.py            # all 9 scripts
    .venv/bin/python tools/decode_mapscript2.py 0xA65C     # one script
    .venv/bin/python tools/decode_mapscript2.py --struct   # per-round structures
"""
import sys

ROM = open("source/zanac.rom", "rb").read()  # cart maps at 0x4000


def at(a, n=1):
    off = a - 0x4000
    return ROM[off:off + n]


def w(a):
    return at(a, 2)[0] | (at(a, 2)[1] << 8)


PTR_TABLE = 0x945C
# Script pointers (idx = stage/round index, entry 8 = first/lowest ROM addr).
SCRIPTS = [w(PTR_TABLE + i * 2) for i in range(9)]

CMD_NAME = {0: "spawn_ctrl", 1: "place_tiles", 2: "col_groups", 3: "tile_copy",
            4: "col_groups+", 5: "stream_slots", 6: "set_E71C",
            7: "disable_grps", 8: "idol_tbl/BANNER", 9: "SCRIPT_JUMP",
            0xA: "vram_glyph", 0xB: "wide_slot", 0xC: "spawn_pace"}


class Desync(Exception):
    pass


def cmd5_len(p):
    """cmd5 body length in bytes: N then per-record 4 or 5 (bit3 of rec byte0)."""
    n = at(p)[0]
    q = p + 1
    for _ in range(n):
        b0 = at(q)[0]
        q += 5 if (b0 & 0x08) else 4
    return q - p


def op_len(cmd, body):
    """Bytes consumed by operands (not counting the 1 cmd byte). `body`=addr of
    first operand. Returns (length, note_string)."""
    nib = cmd & 0xF
    if nib == 0:
        op = at(body)[0]
        if op & 0x04:                       # bit2 -> fall into cmd1 placement
            n = at(body + 1)[0]
            return 1 + 1 + 3 * n, "E12D=%02X +place N=%d" % (op, n)
        return 1, "E12D=%02X" % op
    if nib == 1:
        n = at(body)[0]
        return 1 + 3 * n, "N=%d" % n
    if nib == 2:
        n = at(body)[0]
        return 1 + 5 * n, "N=%d" % n
    if nib == 3:
        n = at(body)[0]
        return 1 + 2 * n, "N=%d" % n
    if nib == 4:
        n = at(body)[0]
        return 1 + 5 * n, "N=%d" % n
    if nib == 5:
        L = cmd5_len(body)
        return L, "N=%d" % at(body)[0]
    if nib == 6:
        return 1, "E71C=%02X" % at(body)[0]
    if nib == 7:
        n = at(body)[0]
        return 1 + n, "N=%d idx=%s" % (n, at(body + 1, n).hex())
    if nib == 8:
        return 2, "idol_tbl=0x%04X" % w(body)
    if nib == 9:
        return 2, "-> 0x%04X" % w(body)
    if nib == 0xA:
        return 1, "fill=%02X" % at(body)[0]
    if nib == 0xB:
        return 7, "E155..=%s" % at(body, 4).hex()
    if nib == 0xC:
        v = at(body)[0]
        s = v - 256 if v & 0x80 else v
        return 1, "nudge=%+d (%02X)" % (s, v)
    raise Desync("bad nibble %X" % nib)


def parse(start, limit=400, follow_jump=False, want_records=False):
    """Yield (addr, row, cmd, note, raw_operand_bytes)."""
    p = start
    last_row = -1
    out = []
    for _ in range(limit):
        row = w(p)
        if row >= 0x8000:                   # sentinel: ran past script into data
            break                           # (idx 0 flows into the ending)
        cmd = at(p + 2)[0]
        body = p + 3
        L, note = op_len(cmd, body)
        raw = bytes(at(body, L))
        out.append((p, row, cmd, note, raw))
        nib = cmd & 0xF
        if nib == 9:                        # script reload / terminal
            if follow_jump and w(body) != start:
                p = w(body)
                last_row = -1
                continue
            break
        p = body + L
        if row < last_row:
            raise Desync("row 0x%04X < prev 0x%04X at 0x%04X" %
                         (row, last_row, out[-1][0]))
        last_row = row
    return out


def show(start):
    print("== script @0x%04X ==" % start)
    for (a, row, cmd, note, raw) in parse(start):
        nib = cmd & 0xF
        hi = cmd >> 4
        print("  0x%04X row=%-5d cmd=%02X %-15s %s"
              % (a, row, cmd, CMD_NAME[nib], note))


def structures(start, rnd):
    """Emit ground-structure-relevant records for a round: the 3-byte cmd1/cmd0
    placement records and cmd8 idol-table pointers."""
    recs = []
    for (a, row, cmd, note, raw) in parse(start):
        nib = cmd & 0xF
        if nib == 8:
            recs.append((row, "IDOL_TBL", "ptr=0x%04X" % w(a + 3)))
        elif nib in (0, 1):
            # extract the 3-byte tile records
            body = a + 3
            if nib == 0:
                if not (raw[0] & 0x04):
                    continue
                n = raw[1]
                base = body + 2
            else:
                n = raw[0]
                base = body + 1
            for k in range(n):
                r = at(base + k * 3, 3)
                recs.append((row, "TILE", "%02X %02X %02X" % (r[0], r[1], r[2])))
    return recs


if __name__ == "__main__":
    args = sys.argv[1:]
    if args and args[0] == "--struct":
        for idx in range(8, -1, -1):
            print("\n#### round/stage index %d  (script @0x%04X)"
                  % (idx, SCRIPTS[idx]))
            for (row, kind, d) in structures(SCRIPTS[idx], idx):
                print("   row=%-5d %-9s %s" % (row, kind, d))
    elif args:
        show(int(args[0], 0))
    else:
        print("master pointer table @0x945C:")
        for i in range(9):
            print("  [%d] 0x%04X" % (i, SCRIPTS[i]))
        for idx in range(8, -1, -1):
            try:
                recs = parse(SCRIPTS[idx])
                print("\n" + "=" * 4 + " idx %d @0x%04X : %d records, ends 0x%04X"
                      % (idx, SCRIPTS[idx], len(recs),
                         recs[-1][0] if recs else 0))
                show(SCRIPTS[idx])
            except Desync as e:
                print("  DESYNC idx %d: %s" % (idx, e))
