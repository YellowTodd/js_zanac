"""Sprint 0060 — screenshot a type-71 warp idol to check the 'smiling face'.

Warp to round 2, break the instant a wide-structure init (0x87C3) loads a
warp-range destination (+0x1D in 0xA6..0xB7), run a few frames so it is drawn,
and grab a PNG.
"""
import sys, os, time, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from zanac_shot import ShotSession

OUT = sys.argv[1] if len(sys.argv) > 1 else "/tmp/warp_idol.png"
RND = int(sys.argv[2]) if len(sys.argv) > 2 else 2


def main():
    with ShotSession() as s:
        msx = s.msx
        msx.cmd("debug break"); msx.cmd("set ::h 0")
        wbp = msx.cmd("debug set_bp 0x425A {} "
                      "{ debug write memory 0xE701 %d; incr ::h; debug cont }" % RND)
        msx.cont(); time.sleep(8.0)
        for _ in range(6):
            msx.key_down(8, 0x01); time.sleep(0.4); msx.key_up(8, 0x01); time.sleep(0.4)
            if int(msx.cmd("set ::h")) > 0:
                break
        try: msx.remove_breakpoint(wbp)
        except Exception: pass
        # invincibility: set flag + keep timer pinned
        msx.write_byte(0xE305, msx.read_byte(0xE305) | 0x80)
        msx.write_byte(0xE31B, 0xFF)
        msx.cmd("debug set_watchpoint write_mem 0xE31B {} "
                "{ debug write memory 0xE31B 0xFF }")
        # break the instant a wide-structure init loads a warp-range destination
        ibp = msx.cmd(r"""debug set_bp 0x87C3 {} {
            set hi [debug read memory [expr {[reg IX]+0x1d}]]
            if {$hi >= 0xA6 && $hi <= 0xB7} { debug break }
        }""")
        msx.cmd("set throttle off")
        msx.cont()
        t0 = time.time(); got = False
        while time.time() - t0 < 60:
            time.sleep(0.5)
            if not msx.is_running():
                got = True; break
        msx.cmd("set throttle on")
        if got:
            ix = int(msx.cmd("reg IX"))
            lo = msx.read_byte(ix + 0x1c); hi = msx.read_byte(ix + 0x1d)
            y = msx.read_byte(ix + 1); x = msx.read_byte(ix + 2)
            print(f"broke on warp idol: type={msx.read_byte(ix)&0x7f} "
                  f"dest=0x{(hi<<8)|lo:04X} @Y{y}/X{x}")
            try: msx.remove_breakpoint(ibp)
            except Exception: pass
            # run ~8 frames so the structure is drawn, then shoot
            msx.cont(); time.sleep(0.25); msx.cmd("debug break")
            s.shot(OUT); time.sleep(0.5)
            print(f"saved {OUT} exists={os.path.exists(OUT)} "
                  f"size={os.path.getsize(OUT) if os.path.exists(OUT) else '-'}")
        else:
            print("no warp-range idol init seen in 40s")


if __name__ == "__main__":
    main()
