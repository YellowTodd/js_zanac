"""Sprint 0033 — visual verification via screenshots.

Captures:
  ref_early.png / ref_logo.png  — real credits from the savestate (logo cycle)
  cr_before.png                 — fresh round-1 gameplay
  cr_after.png                  — after running the chosen credits.tcl
"""
import os, sys, time
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from zanac_shot import ShotSession
from zanackb.zanac_game import ZanacGame

TCL = sys.argv[1] if len(sys.argv) > 1 else "scripts/credits.tcl"
OUT = "/tmp"


def reference():
    with ShotSession(savestate="savestates/game-end.oms") as s:
        s.run(2.0); s.shot(f"{OUT}/ref_early.png"); time.sleep(0.4)
        # Let the credit cycle advance to catch the ZANAC logo entry.
        s.run(9.0); s.shot(f"{OUT}/ref_logo.png"); time.sleep(0.4)
        s.run(6.0); s.shot(f"{OUT}/ref_logo2.png"); time.sleep(0.4)
    print("reference shots done")


def credits_test():
    with ShotSession() as s:
        msx = s.msx
        game = ZanacGame(msx)
        game.wait_for_title(timeout=25)
        game.start_game(timeout=15)
        time.sleep(1.5)
        msx.write_byte(0xE305, msx.read_byte(0xE305) | 0x80)  # invincible
        time.sleep(0.5)
        s.shot(f"{OUT}/cr_before.png"); time.sleep(0.4)
        with open(TCL) as f:
            msx.cmd(f.read())
        msx.cmd("credits")
        s.run(3.0); s.shot(f"{OUT}/cr_after3.png"); time.sleep(0.4)
        s.run(7.0); s.shot(f"{OUT}/cr_after10.png"); time.sleep(0.4)
        # report key RAM
        for a, n in [(0xE700,"E700"),(0xE712,"E712"),(0xE102,"E102")]:
            print(f"  {n}=0x{msx.read_byte(a):02X}")
        print("  e722=0x%04X" % (msx.read_byte(0xE722)|(msx.read_byte(0xE723)<<8)))
        print("  EB00:", bytes(msx.read_memory(0xEB00,16)).hex())
        game.cleanup()
    print(f"credits_test done (tcl={TCL})")


if __name__ == "__main__":
    reference()
    credits_test()
