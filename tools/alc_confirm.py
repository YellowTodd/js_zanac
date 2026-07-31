"""Confirm ALC table mapping deterministically (micro-exec).

The shot-handler ALC block 0x7691..0x76b9 reads E13F (fire cadence), looks up
shot_rate_table[E13F-2] (clamped: E13F>=0x12 -> adv 1), then does
E12F += adv ; E131 += adv ; E13F = 0.

Drive it with controlled E13F and read the advance applied to E12F.
"""
import sys, time
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
from zanackb.zanac_game import ZanacGame

E12F, E131, E13F = 0xE12F, 0xE131, 0xE13F
TABLE = [0x20, 0x10, 0x0a, 0x08, 0x06, 0x05, 0x04, 0x04,
         0x03, 0x03, 0x02, 0x02, 0x02, 0x02, 0x02, 0x02]


def expect(e13f):
    if e13f >= 0x12:
        return 1
    return TABLE[e13f - 2]


def run_block(msx, e13f):
    msx.write_byte(E12F, 0x00)
    msx.write_byte(E131, 0x00)
    msx.write_byte(E13F, e13f)
    msx.cmd("reg ix 0xe100")
    msx.cmd("reg pc 0x7691")
    for _ in range(40):
        msx.cmd("step")
        if int(msx.cmd("reg pc")) == 0x76bc:   # E13F just reset; block done
            break
    return msx.read_byte(E12F), msx.read_byte(E131), msx.read_byte(E13F)


def main():
    with ZanacGame.launch() as game:
        msx = game.client
        game.wait_for_title()
        game.start_game()
        time.sleep(1.5)
        msx.cmd("debug break")

        print("E13F  adv(E12F)  adv(E131)  E13F_after  expected  OK")
        ok_all = True
        for e13f in [0x02, 0x03, 0x04, 0x08, 0x11, 0x12, 0x20]:
            d12f, d131, after = run_block(msx, e13f)
            exp = expect(e13f)
            ok = (d12f == exp and d131 == exp and after == 0)
            ok_all &= ok
            print(f"0x{e13f:02X}   0x{d12f:02X}      0x{d131:02X}      0x{after:02X}"
                  f"        0x{exp:02X}      {'OK' if ok else 'FAIL'}")
        print("\nRESULT:", "ALL OK" if ok_all else "FAILURES")


if __name__ == "__main__":
    main()
