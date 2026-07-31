"""Why does ALC change the instant the ship picks weapon 2 (Field Shutter)?

fire_select(2) calls 0x7591->0x97bc, which scans the entity table (SUB_9b22) for a
free slot and INJECTS a new entity (type 0x45) using a 3-byte record from
fire2_special_table[shot_level] (+3 if round>=5). Confirm by:
  - breakpoints on the inject path (0x97ca) vs skip path (0x97c4)
  - diffing the entity table 0xE300..0xE640 across the pickup.
"""
import sys, os, time
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
from zanackb.zanac_game import ZanacGame

STATE = os.path.abspath("savestates/weapon-2.oms")[:-4]
ETAB_LO, ETAB_HI = 0xE300, 0xE640


def etab(msx):
    return list(msx.read_memory(ETAB_LO, ETAB_HI - ETAB_LO))


def main():
    with ZanacGame.launch() as game:
        msx = game.client
        msx.cmd(f"loadstate {STATE}")
        time.sleep(0.3)
        print(f"round E701={msx.read_byte(0xE701):#04x}  shot_level E10B={msx.read_byte(0xE10B):#04x}  "
              f"fire E14B={msx.read_byte(0xE14B):#04x}")

        # instrument the inject (0x97ca) and skip (0x97c4) branches of 0x97bc
        msx.cmd("set ::inject {}; set ::skip {}; set ::injslot 0")
        bp_in = msx.set_breakpoint(0x97CA, "set ::injslot [reg HL]; lappend ::inject 1")
        bp_sk = msx.set_breakpoint(0x97C4, "lappend ::skip 1")
        # also catch entry to fire_select(2) special path
        msx.cmd("set ::fs2 {}")
        bp_fs = msx.set_breakpoint(0x7591, "lappend ::fs2 [reg HL]")

        before = etab(msx)
        msx.cont()
        # wait for pickup
        t_end = time.time() + 6.0
        while time.time() < t_end:
            time.sleep(0.2)
            if msx.read_byte(0xE14B) == 0x02:
                break
        time.sleep(0.5)
        msx.cmd("debug break")
        after = etab(msx)

        for bp in (bp_in, bp_sk, bp_fs):
            msx.remove_breakpoint(bp)

        n_in = len(msx.cmd("set ::inject").split()) if msx.cmd("set ::inject") else 0
        n_sk = len(msx.cmd("set ::skip").split()) if msx.cmd("set ::skip") else 0
        fs2 = msx.cmd("set ::fs2")
        injslot = msx.cmd("set ::injslot")
        print(f"\nfire_select(2) CALL 0x97bc hits (HL src ptrs): {fs2}")
        print(f"inject-branch (0x97ca) hits: {n_in}   skip-branch (0x97c4) hits: {n_sk}")
        print(f"injected slot (HL at 0x97ca): {injslot}")

        # diff entity table by 0x20-stride slots
        print("\nentity-table slots that changed type/appeared:")
        for off in range(0, ETAB_HI - ETAB_LO, 0x20):
            b, a = before[off], after[off]
            if b != a:
                addr = ETAB_LO + off
                rec_b = " ".join(f"{x:02x}" for x in before[off:off+4])
                rec_a = " ".join(f"{x:02x}" for x in after[off:off+4])
                print(f"  slot {addr:#06x}: type {b:#04x}->{a:#04x}   [{rec_b}] -> [{rec_a}]")


if __name__ == "__main__":
    main()
