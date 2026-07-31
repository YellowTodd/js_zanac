"""Sprint 0049 — Subsystem G group 1 (types 4-18) verification.

Phase 1: confirm the three embedded data tables from ROM.
Phase 2: inject each enemy type (bit7 clear) into a free slot, let the handler
         run its init path for a few frames, read back IX fields vs the decode.
"""
import sys, time
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
from zanackb.zanac_game import ZanacGame

SLOT = 0xE3A0  # slot 5


def slot(msx):
    s = bytes(msx.read_memory(SLOT, 32))
    return s


def show(s):
    return (f"type={s[0]&0x7f} act={s[0]>>7} Y={s[1]} X={s[2]} sat={s[3]:02X} "
            f"col={s[4]:02X} +08={s[8]:02X} +09={s[9]:02X} +0C={s[0x0c]:02X} "
            f"+15={s[0x15]:02X} +19={s[0x19]:02X}")


def inject(msx, game, typ, presets=None):
    # clear slot, set presets, then write type with bit7 clear so init runs
    msx.write_memory(SLOT, bytes(32))
    if presets:
        for off, val in presets.items():
            msx.write_byte(SLOT + off, val)
    msx.write_byte(SLOT + 0x1b, 0xa0)   # +0x1b/1c child ptr -> point at self-ish (E3A0)
    msx.write_byte(SLOT + 0x1c, 0xe3)
    msx.write_byte(SLOT, typ)           # bit7 clear -> handler init path
    time.sleep(0.15)                    # a few frames
    return slot(msx)


def main():
    passed = []
    failed = []
    with ZanacGame.launch() as game:
        msx = game.client

        print("=== Phase 1: data tables from ROM ===")
        bspt = bytes(msx.read_memory(0x7AF7, 16))
        print("base_spawner_spawn_table:", ' '.join(f'{b:02X}' for b in bspt))
        assert bspt == bytes([0x0a,0x1e,0x10,0x08,0x16,0x0a,0x17,0x08,
                              0x30,0x06,0x08,0x08,0x41,0x06,0x24,0x1e]), "BSPT mismatch"
        passed.append("base_spawner_spawn_table bytes")

        ptr = bytes(msx.read_memory(0x7B7B, 8))
        print("teruzo ptr table:", ' '.join(f'{b:02X}' for b in ptr))
        assert ptr == bytes([0x83,0x7b,0x98,0x7b,0xae,0x7b,0xcc,0x7b]), "teruzo ptr mismatch"
        passed.append("teruzo pointer table -> 7b83/7b98/7bae/7bcc")
        for addr in (0x7B83, 0x7B98, 0x7BAE, 0x7BCC):
            b = bytes(msx.read_memory(addr, 3))
            print(f"  block {addr:04X}: Y={b[0]} X={b[1]} col={b[2]:02X}")

        umt = bytes(msx.read_memory(0x79B7, 7))
        print("umber_burst_param_table:", ' '.join(f'{b:02X}' for b in umt))
        assert umt == bytes([0x04,0x05,0x02,0x07,0x03,0x06,0x01]), "umber tbl mismatch"
        passed.append("umber_burst_param_table bytes")

        print("\n=== Phase 2: inject + init ===")
        game.wait_for_title(); game.start_game(); time.sleep(1.5)

        # box (type 4): preset countdown +0x03=1 so it reveals immediately
        s = inject(msx, game, 0x04, {0x03: 0x01})
        print("box     :", show(s))
        if s[3] == 0xD4 and s[0x19] == 0x05 and s[8] == 0xC0:
            passed.append("box reveal: sat=D4 hp=5 vyfrac=C0")
        else: failed.append(f"box: {show(s)}")

        # umber (type 7)
        s = inject(msx, game, 0x07)
        print("umber   :", show(s))
        # vy starts 3 then Y-homing reduces it; check stable init fields
        if s[3] == 0xDC and s[2] == 120 and s[0x0c] == 0x09 and s[0x15] == 0x10:
            passed.append("umber init: sat=DC X=120 bflags=09 yacc=10 (vy 3->homing)")
        else: failed.append(f"umber: {show(s)}")

        # duster (type 10)
        s = inject(msx, game, 0x0A)
        print("duster  :", show(s))
        if s[3] == 0x58 and s[4] == 0x89 and s[0x0c] == 0x13 and s[9] == 0x03:
            passed.append("duster init: sat=58 col=89 bflags=13 vy=3")
        else: failed.append(f"duster: {show(s)}")

        # teruzo (type 12): expect sat=0x60, Y/X from a block, col 8A or 89
        s = inject(msx, game, 0x0C)
        print("teruzo  :", show(s))
        # X drifts via bflags X-motion; corner identified by (Y, col)
        corner = {(112,0x8A),(32,0x89)}
        if s[3] == 0x60 and s[0x0c] == 0x03 and (s[1], s[4]) in corner:
            passed.append(f"teruzo init: sat=60 corner Y={s[1]} col={s[4]:02X} (X drifts)")
        else: failed.append(f"teruzo: {show(s)}")

        # luster (type 16): expect sat=0x74 (or 0x78 after a flip), col 8E
        s = inject(msx, game, 0x10)
        print("luster  :", show(s))
        if s[3] in (0x74, 0x78) and s[4] == 0x8E and s[9] == 0x02:
            passed.append(f"luster init: sat={s[3]:02X} col=8E vy=2 X={s[2]}")
        else: failed.append(f"luster: {show(s)}")

    print("\n=== RESULTS ===")
    for p in passed: print("  PASS", p)
    for f in failed: print("  FAIL", f)
    print(f"\n{len(passed)} passed, {len(failed)} failed")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
