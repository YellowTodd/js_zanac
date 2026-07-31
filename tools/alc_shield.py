"""Map weapon-2 entities: which one is the shield (tracks ship), which emits a wave."""
import sys, os, time
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
from zanackb.zanac_game import ZanacGame

STATE = os.path.abspath("savestates/weapon-2.oms")[:-4]


def dump(msx, tag):
    sx = msx.read_byte(0xE302); sy = msx.read_byte(0xE301)
    print(f"\n[{tag}] ship slot0 (Y={sy},X={sx})  E380={msx.read_byte(0xE380):#04x} "
          f"({msx.read_byte(0xE381):3},{msx.read_byte(0xE382):3})")
    for a in range(0xE300, 0xE640, 0x20):
        t = msx.read_byte(a)
        if t:
            print(f"  {a:#06x} type={t:#04x} Y={msx.read_byte(a+1):3} X={msx.read_byte(a+2):3} "
                  f"+18={msx.read_byte(a+0x18):#04x} +19={msx.read_byte(a+0x19):#04x}")


def main():
    with ZanacGame.launch() as game:
        msx = game.client
        msx.cmd(f"loadstate {STATE}")
        time.sleep(0.3)
        t_end = time.time() + 6
        while time.time() < t_end and msx.read_byte(0xE14B) != 2:
            time.sleep(0.2)
        time.sleep(0.3)
        dump(msx, "after pickup")
        # steer left a while
        game.steer(left=True); time.sleep(1.2); game.steer()  # release
        dump(msx, "after steer LEFT")
        game.steer(right=True); time.sleep(1.5); game.steer()
        dump(msx, "after steer RIGHT")


if __name__ == "__main__":
    main()
