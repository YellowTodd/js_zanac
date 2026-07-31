#!/usr/bin/env python3
"""Byte-exact Zanac sound-track decoder (sprint 0064).

Walks all 27 sound events from the pointer table at 0x5234, parsing each event
header (voice descriptors) and decoding every voice stream with the exact
grammar of `advance_track_stream` (0x4F4A) + `load_sound_event` (0x5199), then
reports coverage of the whole music-data region 0x5236-0x5A11.

Grammar (verified against ROM sprint 0064):

  Event header (load_sound_event 0x5199):
    [N]                       voice count
    per voice: [D]            slot descriptor (slot = 0xE20C + D*27)
      if cfg0 != 0: [cfg0..cfg7]  8 bytes -> slot[0..7]; stream ptr = cfg6:cfg7
      if cfg0 == 0: (just the 0 byte) silenced voice, 2-byte descriptor

  Stream bytes (advance_track_stream 0x4F4A), classified by the first byte:
    0x00-0x7F  NOTE   (+ optional duration token if next byte >= 0xDF)
    0x80-0x8C  COMMAND (jump table @0x4F6C)
    0xDF-0xFF  REPLAY previous note (+ its own duration token semantics)

  Duration token (the byte after a note, or a replay byte, if >= 0xDF):
    0xDF        -> +1 raw duration byte follows
    0xE0-0xFF   -> index (token-0xE0) into duration table @0x526C

  Command operand lengths (jump table @0x4F6C -> handlers):
    0x80 JUMP LL HH (2, redirect)   0x87 PLAY_EVENT nn (1)
    0x81 LOOP LL HH (2, cond branch) 0x88 SET_LOOPCNT nn (1)
    0x82 END        (0, terminator)  0x89 SET_NOISE   nn (1)
    0x83 JMP_IF_ENV LL HH (2, cond)  0x8A IDX_TRANSPOSE LL HH (2)
    0x84 SET_CURVE nn (1)            0x8B VOL_ENV cc rr (2)
    0x85 TRANSPOSE nn (1)           0x8C PITCH_SLIDE ff rr (2)
    0x86 VOL_ADJ  nn (1)

Usage:
    .venv/bin/python tools/decode_tracks.py            # coverage summary
    .venv/bin/python tools/decode_tracks.py --score 1  # human score for event 1
    .venv/bin/python tools/decode_tracks.py --score all
"""
import sys

ROM = open("source/zanac.rom", "rb").read()
BASE = 0x4000
REGION = (0x5236, 0x5A10)          # music data (inclusive); 0x5A11 (CD..) is
#                                    already code (CALL 0x46BC) — the sprint's
#                                    stated 0x5A11 endpoint overshoots by 1.

PTR_TABLE = 0x5234                  # entry 0 = sentinel; 1..27 valid
DUR_TABLE = 0x526C                  # 0xE0-token duration lookup

NOTE_NAMES = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"]

CMD_LEN = {0x80: 2, 0x81: 2, 0x82: 0, 0x83: 2, 0x84: 1, 0x85: 1, 0x86: 1,
           0x87: 1, 0x88: 1, 0x89: 1, 0x8A: 2, 0x8B: 2, 0x8C: 2}
CMD_NAME = {0x80: "JUMP", 0x81: "LOOP", 0x82: "END", 0x83: "JMP_IF_ENV",
            0x84: "SET_CURVE", 0x85: "TRANSPOSE", 0x86: "VOL_ADJ",
            0x87: "PLAY_EVENT", 0x88: "SET_LOOPCNT", 0x89: "SET_NOISE",
            0x8A: "IDX_TRANSPOSE", 0x8B: "VOL_ENV", 0x8C: "PITCH_SLIDE"}


def at(a, n=1):
    return ROM[a - BASE: a - BASE + n]


def b(a):
    return ROM[a - BASE]


def w(a):
    return b(a) | (b(a + 1) << 8)


def event_ptr(ev):
    return w(PTR_TABLE + ev * 2)


def parse_header(ev):
    """Return (hdr_end_addr, [voice dicts]). voice = {D, cfg, stream}."""
    p = event_ptr(ev)
    n = b(p)
    p += 1
    voices = []
    for _ in range(n):
        D = b(p)
        p += 1
        cfg0 = b(p)
        if cfg0 == 0:
            voices.append({"D": D, "cfg": bytes([0]), "stream": None})
            p += 1
        else:
            cfg = bytes(at(p, 8))
            stream = cfg[6] | (cfg[7] << 8)
            voices.append({"D": D, "cfg": cfg, "stream": stream})
            p += 8
    return p, voices


def note_len(p):
    """Bytes a NOTE token (0x00-0x7F at p) consumes, incl. duration token."""
    t = b(p + 1)
    if t >= 0xDF:
        return 3 if t == 0xDF else 2
    return 1


def replay_len(p):
    return 2 if b(p) == 0xDF else 1     # 0xDF -> raw byte follows


def walk_voice(stream, covered, note_types, idx_targets=None):
    """DFS over a voice's control flow from `stream`. Marks every consumed byte
    offset in `covered` (a set); records opcode class in note_types for the
    unknown-op check; collects IDX_TRANSPOSE (0x8A) table pointers in
    idx_targets. Returns list of anomalies."""
    anomalies = []
    seen = set()
    stack = [stream]
    while stack:
        p = stack.pop()
        while True:
            if p in seen:
                break
            if not (REGION[0] <= p <= REGION[1] + 2):
                anomalies.append("stream escaped region at 0x%04X" % p)
                break
            seen.add(p)
            byte = b(p)
            if byte <= 0x7F:                      # NOTE
                L = note_len(p)
                for k in range(L):
                    covered.add(p + k)
                note_types.add("note")
                p += L
            elif byte >= 0xDF:                    # REPLAY
                L = replay_len(p)
                for k in range(L):
                    covered.add(p + k)
                note_types.add("replay")
                p += L
            elif byte in CMD_LEN:                 # COMMAND
                L = CMD_LEN[byte]
                for k in range(1 + L):
                    covered.add(p + k)
                note_types.add("cmd_%02X" % byte)
                if byte == 0x8A and idx_targets is not None:
                    idx_targets.add(w(p + 1))     # per-loop transpose table
                if byte == 0x82:                  # END
                    break
                if byte in (0x80,):               # unconditional JUMP
                    tgt = w(p + 1)
                    stack.append(tgt)
                    break
                if byte in (0x81, 0x83):          # conditional branch
                    tgt = w(p + 1)
                    stack.append(tgt)             # branch target
                    p += 1 + L                    # ...and fall through
                    continue
                p += 1 + L                        # linear command
            else:                                 # 0x8D-0xDE = invalid opcode
                anomalies.append("unknown opcode 0x%02X at 0x%04X" % (byte, p))
                covered.add(p)
                break
    return anomalies


# Non-stream engine tables inside the region (decoded sprint 0028):
#   0x526C-0x527C  note-duration table (17 entries, indexed by 0xE0-token)
#   0x527D-0x52E1  volume-curve selector + curves 1-7 (apply_amp_curve 0x5099)
ENGINE_TABLES = (0x526C, 0x52E1)
# Trailing filler between the last event's END and the code at 0x5A11:
TAIL_PAD = (0x5A0F, 0x5A10)        # FF FF ; 0x5A11 (CD..) is code (CALL 0x46BC)


def decode_all():
    covered = set()
    note_types = set()
    idx_targets = set()
    all_anom = []
    # pointer table (entries 0..27 = 56 bytes 0x5234..0x526B)
    for a in range(PTR_TABLE, PTR_TABLE + 56):
        covered.add(a)
    per_event = []
    for ev in range(1, 28):
        hdr_end, voices = parse_header(ev)
        start = event_ptr(ev)
        for a in range(start, hdr_end):           # header bytes
            covered.add(a)
        anoms = []
        for v in voices:
            if v["stream"] is not None:
                anoms += walk_voice(v["stream"], covered, note_types,
                                    idx_targets)
        all_anom += ["ev%d: %s" % (ev, a) for a in anoms]
        per_event.append((ev, start, hdr_end, voices, anoms))
    # engine tables + tail padding
    for a in range(ENGINE_TABLES[0], ENGINE_TABLES[1] + 1):
        covered.add(a)
    for a in range(TAIL_PAD[0], TAIL_PAD[1] + 1):
        covered.add(a)
    # IDX_TRANSPOSE (0x8A) per-loop tables: each runs from its target until the
    # next already-covered byte (bounded by neighbouring stream/table data).
    for tgt in idx_targets:
        a = tgt
        while REGION[0] <= a <= REGION[1] and a not in covered:
            covered.add(a)
            a += 1
    return covered, note_types, all_anom, per_event


def coverage_report():
    covered, note_types, anoms, per_event = decode_all()
    lo, hi = REGION
    total = hi - lo + 1
    hit = sum(1 for a in range(lo, hi + 1) if a in covered)
    print("== Sound-track coverage (0x%04X-0x%04X, %d bytes) ==" %
          (lo, hi, total))
    print("events 1-27, %d voices total" %
          sum(len(v[3]) for v in per_event))
    # gaps
    gaps = []
    a = lo
    while a <= hi:
        if a not in covered:
            g0 = a
            while a <= hi and a not in covered:
                a += 1
            gaps.append((g0, a - 1))
        else:
            a += 1
    print("covered %d/%d = %.1f%%   gaps: %d" %
          (hit, total, 100.0 * hit / total, len(gaps)))
    for (g0, g1) in gaps:
        print("   GAP 0x%04X-0x%04X (%d B): %s" %
              (g0, g1, g1 - g0 + 1, at(g0, min(16, g1 - g0 + 1)).hex()))
    print("opcode classes seen: %s" % ", ".join(sorted(note_types)))
    if anoms:
        print("ANOMALIES:")
        for x in anoms:
            print("   " + x)
    else:
        print("no anomalies (every opcode known, no stream escaped the region)")
    # chain targets (0x87)
    print("\n0x87 PLAY_EVENT chains found:")
    for (ev, start, hdr_end, voices, _) in per_event:
        for v in voices:
            if v["stream"] is None:
                continue
            p = v["stream"]
            for _ in range(4000):
                if not (lo <= p <= hi):
                    break
                x = b(p)
                if x <= 0x7F:
                    p += note_len(p)
                elif x >= 0xDF:
                    p += replay_len(p)
                elif x in CMD_LEN:
                    if x == 0x87:
                        print("   ev%d -> plays ev%d (at 0x%04X)"
                              % (ev, b(p + 1), p))
                    if x == 0x82:
                        break
                    if x == 0x80:
                        break
                    p += 1 + CMD_LEN[x]
                else:
                    break


def score(ev):
    hdr_end, voices = parse_header(ev)
    print("== event %d @0x%04X : %d voices ==" % (ev, event_ptr(ev), len(voices)))
    for vi, v in enumerate(voices):
        print(" voice %d: slot D=%d cfg=%s stream=0x%04X"
              % (vi, v["D"], v["cfg"].hex(),
                 v["stream"] if v["stream"] else 0))
        if v["stream"] is None:
            print("   (silenced)")
            continue
        p = v["stream"]
        out = []
        seen = set()
        for _ in range(600):
            if p in seen or not (REGION[0] <= p <= REGION[1] + 2):
                break
            seen.add(p)
            x = b(p)
            if x <= 0x7F:
                L = note_len(p)
                if x == 0:
                    tok = "rest"
                else:
                    tok = "%s%d" % (NOTE_NAMES[(x - 1) % 12], (x - 1) // 12)
                dur = ""
                if L > 1:
                    dur = " d=%s" % at(p + 1, L - 1).hex()
                out.append(tok + dur)
                p += L
            elif x >= 0xDF:
                L = replay_len(p)
                out.append("~%s" % at(p, L).hex())
                p += L
            elif x in CMD_LEN:
                L = CMD_LEN[x]
                ops = at(p + 1, L).hex()
                out.append("[%s %s]" % (CMD_NAME[x], ops))
                if x == 0x82:
                    break
                if x == 0x80:
                    out.append("->0x%04X" % w(p + 1))
                    break
                p += 1 + L
            else:
                out.append("?%02X" % x)
                break
        # wrap
        line = " "
        for tok in out:
            if len(line) + len(tok) > 78:
                print("  " + line)
                line = " "
            line += " " + tok
        print("  " + line)


if __name__ == "__main__":
    a = sys.argv[1:]
    if a and a[0] == "--score":
        if a[1] == "all":
            for ev in range(1, 28):
                score(ev)
        else:
            score(int(a[1]))
    else:
        coverage_report()
