#!/usr/bin/env python3
"""Live spot-check for the sound-track decoder (sprint 0064).

Title screen auto-plays event 3. Breakpoint the note handler (0x5030), where
A = the note byte being started and IX = the voice slot, log a burst without
halting the CPU, then compare the per-slot note subsequence to the static
decode of event 3.
"""
import sys, time
sys.path.insert(0, "tools")
from zanackb.zanac_game import ZanacGame

SLOT = {2: 0xE242, 3: 0xE25D, 4: 0xE278}   # 0xE20C + D*27

# static decode of ev3 voice 0 (slot D=2) raw note bytes, first ~24
import decode_tracks as t


def static_notes(ev, voice_idx, n=24):
    he, voices = t.parse_header(ev)
    p = voices[voice_idx]["stream"]
    out = []
    seen = set()
    while len(out) < n and p not in seen and t.REGION[0] <= p <= t.REGION[1]:
        seen.add(p)
        x = t.b(p)
        if x <= 0x7F:
            out.append(x)
            p += t.note_len(p)
        elif x >= 0xDF:
            p += t.replay_len(p)
        elif x in t.CMD_LEN:
            if x == 0x82:
                break
            if x == 0x80:
                p = t.w(p + 1)
                continue
            p += 1 + t.CMD_LEN[x]
        else:
            break
    return out


def main():
    exp = static_notes(3, 0, 24)
    print("static ev3 voice0 (slot 0xE242) notes:",
          " ".join("%02X" % x for x in exp))
    with ZanacGame.launch("source/zanac.rom") as game:
        msx = game.client
        game.wait_for_title()
        time.sleep(1.0)
        msx.cmd("set ::log {}")
        bp = msx.cmd("debug set_bp 0x5030 {} "
                     "{lappend ::log [list [reg IX] [reg A]]}")
        time.sleep(2.5)
        raw = msx.cmd("set ::log")
        try:
            msx.cmd("debug remove_bp %s" % bp)
        except Exception:
            pass
    # raw is a TCL list of "{ix a}" pairs (decimals)
    pairs = []
    tok = raw.replace("{", " ").replace("}", " ").split()
    for i in range(0, len(tok) - 1, 2):
        try:
            pairs.append((int(tok[i]), int(tok[i + 1])))
        except ValueError:
            pass
    live = [a & 0x7F for (ix, a) in pairs if ix == 0xE242]
    print("live   slot 0xE242 notes:", " ".join("%02X" % x for x in live[:24]))
    # compare longest common prefix
    m = 0
    for e, l in zip(exp, live):
        if e == l:
            m += 1
        else:
            break
    print("matching leading notes: %d / %d" % (m, min(len(exp), len(live))))
    print("total bp hits: %d (slot E242: %d)" % (len(pairs), len(live)))


if __name__ == "__main__":
    main()
