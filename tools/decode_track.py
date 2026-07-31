#!/usr/bin/env python3
"""Disassemble Zanac PSG sound-engine track streams.

Sprint 0028. Decodes the per-voice byte format parsed by advance_track_stream
(0x4F4A): notes, duration tokens, and the 0x80-0x8C command set.

Usage:
    .venv/bin/python tools/decode_track.py [event]
    .venv/bin/python tools/decode_track.py --addr 0x5458   # raw stream at addr

Default lists every event's header and disassembles event 3 (title music).
"""
import sys

ROM = open("source/zanac.rom", "rb").read()  # maps at 0x4000


def at(a, n):
    off = a - 0x4000
    return ROM[off:off + n]


def b16(a):
    x = at(a, 2)
    return x[0] | (x[1] << 8)


DUR = at(0x526C, 19)  # note-duration table, index = token - 0xE0
CMD = {
    0x80: ("JUMP", 2), 0x81: ("LOOP", 2), 0x82: ("END", 0),
    0x83: ("JUMP_IF_ENV", 2), 0x84: ("SET_CURVE", 1), 0x85: ("TRANSPOSE", 1),
    0x86: ("VOL_ADJ", 1), 0x87: ("PLAY_EVENT", 1), 0x88: ("SET_LOOPCNT", 1),
    0x89: ("SET_NOISE", 1), 0x8A: ("IDX_TRANSPOSE", 2), 0x8B: ("VOL_ENV", 2),
    0x8C: ("PITCH_SLIDE", 2),
}
NOTES = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"]


def notename(v):
    if v == 0:
        return "REST"
    n = v - 1
    return "%s%d" % (NOTES[n % 12], n // 12)


def dur(tok, p):
    if tok == 0xDF:
        return "d=%d(raw)" % at(p + 1, 1)[0], 2
    idx = tok - 0xE0
    if 0 <= idx < len(DUR):
        return "d=%d" % DUR[idx], 1
    return "d=?tok%02x" % tok, 1


def disasm(start, limit=400):
    p, out, n = start, [], 0
    while n < limit:
        a, b = p, at(p, 1)[0]
        if b < 0x80:
            nxt = at(p + 1, 1)[0]
            if nxt >= 0xDF:
                dt, c = dur(nxt, p + 1)
                out.append("0x%04x: %-4s %s" % (a, notename(b), dt))
                p += 1 + c
            else:
                out.append("0x%04x: %-4s (dur=prev)" % (a, notename(b)))
                p += 1
        elif b >= 0xDF:
            dt, c = dur(b, p)
            out.append("0x%04x: REPLAY %s" % (a, dt))
            p += c
        elif b in CMD:
            name, no = CMD[b]
            ops = at(p + 1, no)
            ot = ("0x%04x" % (ops[0] | (ops[1] << 8)) if no == 2
                  else "0x%02x" % ops[0] if no == 1 else "")
            out.append("0x%04x: %s %s" % (a, name, ot))
            p += 1 + no
            if b in (0x82, 0x80):  # END / JUMP terminate linear decode
                break
        else:
            out.append("0x%04x: ??? 0x%02x" % (a, b))
            p += 1
        n += 1
    return out


def voices(event):
    hdr = b16(0x5234 + event * 2)
    N = at(hdr, 1)[0]
    p, vs = hdr + 1, []
    for v in range(N):
        params = at(p + 1, 8)
        vs.append((at(p, 1)[0], params, params[6] | (params[7] << 8)))
        p += 9
    return hdr, vs


def main():
    if len(sys.argv) >= 3 and sys.argv[1] == "--addr":
        for line in disasm(int(sys.argv[2], 16)):
            print("  " + line)
        return
    print("=== event pointer table ===")
    for i in range(1, 28):
        print(" event %2d -> 0x%04x" % (i, b16(0x5234 + i * 2)))
    event = int(sys.argv[1], 0) if len(sys.argv) >= 2 else 3
    hdr, vs = voices(event)
    print("\n=== event %d @0x%04x: %d voices ===" % (event, hdr, len(vs)))
    for i, (desc, params, ptr) in enumerate(vs):
        print(" voice%d slot=0x%04x cfg=0x%02x amp=0x%02x curve=0x%02x "
              "transp=0x%02x tempo=0x%02x chan=%d stream=0x%04x"
              % (i, 0xE20C + desc * 27, params[0], params[1], params[2],
                 params[3], params[4], params[5], ptr))
    for i, (desc, params, ptr) in enumerate(vs):
        print("\n--- voice%d stream @0x%04x ---" % (i, ptr))
        for line in disasm(ptr):
            print("  " + line)


if __name__ == "__main__":
    main()
