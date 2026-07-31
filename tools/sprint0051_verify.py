"""Sprint 0051 — Subsystem G group 3 verification.
Inject each type, run init, check decoded fields. Confirm tables from ROM.
"""
import sys, time
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
from zanackb.zanac_game import ZanacGame

SLOT = 0xE3A0


def inj(msx, typ, presets=None):
    msx.write_memory(SLOT, bytes(32))
    msx.write_byte(SLOT + 0x1b, 0xa0); msx.write_byte(SLOT + 0x1c, 0xe3)
    if presets:
        for o, v in presets.items():
            msx.write_byte(SLOT + o, v)
    msx.write_byte(SLOT, typ)
    time.sleep(0.15)
    return bytes(msx.read_memory(SLOT, 32))


def main():
    p, f = [], []
    with ZanacGame.launch() as game:
        msx = game.client
        # tables
        tt = bytes(msx.read_memory(0x77EA, 30)); st = bytes(msx.read_memory(0x7808, 30))
        ct = bytes(msx.read_memory(0x8EAF, 8))
        print("type_tbl 0x77ea:", ' '.join(f'{b:02X}' for b in tt[:16]), "...")
        print("sat_tbl  0x7808:", ' '.join(f'{b:02X}' for b in st[:16]), "...")
        print("desc_col 0x8eaf:", ' '.join(f'{b:02X}' for b in ct))
        (p if all(b in (4,5,6) for b in tt) else f).append("proto_box_type_table all 4/5/6")
        (p if ct == bytes([0x81,0x83,0x84,0x86,0x87,0x89,0x8a,0x8d]) else f).append("large_descender_color_table")

        game.wait_for_title(); game.start_game(); time.sleep(1.5)

        def chk(name, typ, cond, presets=None):
            s = inj(msx, typ, presets)
            print(f"{name:10s} t{typ}: type={s[0]:02X} sat={s[3]:02X} col={s[4]:02X} "
                  f"+09={s[9]:02X} +0C={s[0x0c]:02X} +15={s[0x15]:02X} +17={s[0x17]:02X} "
                  f"+19={s[0x19]:02X} +1B={s[0x1b]:02X} +1C={s[0x1c]:02X} +1F={s[0x1f]:02X}")
            (p if cond(s) else f).append(f"{name}")

        chk("pair_frag", 41, lambda s: s[3]==0x1c and s[0x0c]==0x03, {0x1a:0x03})
        chk("proto_bull", 42, lambda s: s[0]==0xa5, {0x1a:0x03})
        chk("proto_frag", 43, lambda s: s[0]==0xa6, {0x1a:0x03})
        chk("grnd_struc", 44, lambda s: s[3]==0x40 and s[4]==0x83 and s[0x0c]==0x03)
        chk("lbar_var", 45, lambda s: s[4]==0x8f and s[0x0c]==0x03 and s[0x19]==0x03, {0x1a:0x02})
        chk("sig_single", 56, lambda s: s[3]==0x70 and s[0x0c]==0x03 and s[0x1f]==0x20)
        chk("descend_a", 57, lambda s: s[3]==0x6c and s[0x0c]==0x03)
        chk("descend_b", 58, lambda s: s[3]==0x68 and s[0x0c]==0x03)
        chk("sideways", 59, lambda s: s[3]==0x70 and s[0x0c]==0x03, {0x1a:0x04})
        chk("lg_descend", 61, lambda s: s[3]==0xf8 and s[9]==0x02 and s[0x0c] in (0x00, 0x01))
        chk("invis_rise", 62, lambda s: s[3]==0x00 and s[4]==0x87 and s[9]==0xff, {0x01:0x60})
        chk("proto_strc", 64, lambda s: (s[0] & 0x7f) != 0x40)  # converted to a table type
        chk("med_circle", 67, lambda s: s[3] in (0x20, 0x14) and s[0x1b]!=0x00 and s[0x1c]==0x1e)

    print("\n=== RESULTS ===")
    for x in p: print("  PASS", x)
    for x in f: print("  FAIL", x)
    print(f"\n{len(p)} passed, {len(f)} failed")
    return 1 if f else 0


if __name__ == "__main__":
    sys.exit(main())
