"""Sprint 0050 — Subsystem G group 2 (types 20-38) verification.
Inject each type (bit7 clear), run init a few frames, check decoded fields.
"""
import sys, time
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
from zanackb.zanac_game import ZanacGame

SLOT = 0xE3A0


def inj(msx, typ, presets=None):
    msx.write_memory(SLOT, bytes(32))
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
        print("anim A 0x7e68:", ' '.join(f'{b:02X}' for b in msx.read_memory(0x7E68, 8)))
        print("anim B 0x7e70:", ' '.join(f'{b:02X}' for b in msx.read_memory(0x7E70, 8)))
        a = bytes(msx.read_memory(0x7E68, 8)); b = bytes(msx.read_memory(0x7E70, 8))
        (p if a == bytes([0xAC,0x8E,0xB0,0x8E,0xB4,0x8E,0xB8,0x8E]) else f).append("anim_a 0x7e68")
        (p if b == bytes([0xAC,0x87,0xB0,0x87,0xB4,0x87,0xB8,0x87]) else f).append("anim_b 0x7e70")

        game.wait_for_title(); game.start_game(); time.sleep(1.5)

        def chk(name, typ, cond, presets=None):
            s = inj(msx, typ, presets)
            print(f"{name:10s}: sat={s[3]:02X} col={s[4]:02X} +08={s[8]:02X} +09={s[9]:02X} "
                  f"+0C={s[0x0c]:02X} +11={s[0x11]:02X} +13={s[0x13]:02X} +15={s[0x15]:02X} "
                  f"+16={s[0x16]:02X} +19={s[0x19]:02X} +1D={s[0x1d]:02X}")
            (p if cond(s) else f).append(f"{name}: {cond.__doc__}")

        chk("lead_homing", 20, lambda s: s[3]==0x1c and s[0x0c]==0x0b and s[0x13]==0xff and s[0x15]==0x0c)
        chk("light_bar", 21, lambda s: s[3]==0x18 and s[0x0c]==0x03, {0x1a:0x04})
        chk("veybar", 22, lambda s: s[3]==0x84 and s[4]==0x83 and s[0x0c]==0x09 and s[0x15]==0x14)
        chk("veybar_fst", 24, lambda s: s[3]==0x84 and s[0x0c]==0x1b and s[0x16]==0x10 and s[4]==0x89)
        chk("swooper_a", 26, lambda s: s[0x11]==0x68 and s[0x0c]==0x0f and s[0x1d]==0x25)
        chk("swooper_b", 28, lambda s: s[0x11]==0x70 and s[0x0c]==0x0f and s[0x1d]==0x3b)
        chk("grnd_swoop", 30, lambda s: s[3]==0xec and s[0x0c]==0x01 and s[8]==0x80)
        chk("flashing", 36, lambda s: s[3]==0x34 and s[0x19]==0x10)
        chk("lead_bullet", 37, lambda s: s[3]==0x1c and s[4]==0x8f and s[0x0c]==0x03)
        chk("burst_frag", 38, lambda s: s[3]==0x1c and s[0x0c]==0x03, {0x1a:0x02})

    print("\n=== RESULTS ===")
    for x in p: print("  PASS", x)
    for x in f: print("  FAIL", x)
    print(f"\n{len(p)} passed, {len(f)} failed")
    return 1 if f else 0


if __name__ == "__main__":
    sys.exit(main())
