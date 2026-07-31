#!/usr/bin/env python3
"""Parse Zanac level map-script streams (sprint 0029).

Each map command is [row:2 LE][cmd:1][operands]. The command byte's low nibble
selects a handler (jump table at 0x94EB). Row triggers are nondecreasing.

Simple commands (2,6,7,8,9,C) have known operand lengths and are decoded fully;
variable/greeble commands (0,1,3,4,5,A,B) are printed as a hex blob up to the
next plausible nondecreasing row trigger.

Usage:
    .venv/bin/python tools/decode_mapscript.py            # list pointer table
    .venv/bin/python tools/decode_mapscript.py 0xA65C     # parse a script
"""
import sys

ROM = open("source/zanac.rom", "rb").read()  # maps at 0x4000


def at(a, n):
    off = a - 0x4000
    return ROM[off:off + n]


def w(a):
    x = at(a, 2)
    return x[0] | (x[1] << 8)


NAMES = {0: "spawn_ctrl", 1: "spawn_stream", 2: "col_groups", 3: "tile_ptr3",
         4: "tile_ptr4", 5: "stream_slots", 6: "set_E71C", 7: "disable_groups",
         8: "wide_ptr", 9: "splice", 0xA: "greeble_ents", 0xB: "wide_struct",
         0xC: "adj_pos"}


def ptr_table():
    print("master script pointer table @0x945C:")
    for i in range(9):
        print("  [%d] 0x%04X" % (i, w(0x945C + i * 2)))


def parse(start, limit=40):
    p = start
    last_row = -1
    for _ in range(limit):
        row = w(p)
        cmd = at(p + 2, 1)[0]
        nib = cmd & 0xF
        name = NAMES.get(nib, "?")
        hdr = "0x%04X: row=%-5d cmd=0x%02X %-13s" % (p, row, cmd, name)
        body = p + 3
        if nib == 6 or nib == 0xC:          # 1 operand
            print(hdr + "op=%02X" % at(body, 1)[0]); p = body + 1
        elif nib == 9:                       # 2-byte splice ptr, stream jumps
            print(hdr + "-> 0x%04X (splice)" % w(body)); return
        elif nib == 8:                       # 2-byte ptr
            print(hdr + "ptr=0x%04X" % w(body)); p = body + 2
        elif nib == 7:                       # count + N indices
            n = at(body, 1)[0]
            print(hdr + "N=%d idx=%s" % (n, at(body + 1, n).hex()))
            p = body + 1 + n
        elif nib == 2:                       # count + N*5
            n = at(body, 1)[0]
            recs = []
            for k in range(n):
                r = at(body + 1 + k * 5, 5)
                recs.append("slot%d{st=%02X par=%02X ptr=%04X}"
                            % (r[0], r[1], r[2], r[3] | (r[4] << 8)))
            print(hdr + "N=%d %s" % (n, " ".join(recs)))
            p = body + 1 + n * 5
        else:                                # variable: scan to next row trigger
            q = body
            while q < body + 32 and not (w(q) >= row and at(q + 2, 1)[0] & 0xF0
                                         in (0x00, 0x10, 0x20, 0x80, 0x40, 0x50,
                                             0x60, 0x90, 0xA0, 0xB0, 0xC0)):
                q += 1
            print(hdr + "[var] %s" % at(body, q - body).hex())
            p = q
        if row < last_row:
            print("  ! row decreased — parse desync, stopping"); return
        last_row = row


if __name__ == "__main__":
    if len(sys.argv) >= 2:
        parse(int(sys.argv[1], 0))
    else:
        ptr_table()
