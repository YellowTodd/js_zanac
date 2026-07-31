"""Probe: does round 2's idx-88 invisible totem spawn on the FIRST (normal)
pass of the map script, or only after the loop/warp tail re-enters the stream?

Enters round 2 normally (force E701=2 at 0x425A), then logs every
wide-structure init at 0x87C3 with:
  type, +0x18, +0x03 (idol idx), +0x1C/1D (dest), Y, X,
  E720 idol-table ptr, E704 script PC, E702 row, E701 round.
Also watches writes to 0xE720 (cmd-8 executions) to timestamp table swaps.

Run: .venv/bin/python tools/probe_idx88.py [seconds (default 120)]
"""
import sys
import time

sys.path.insert(0, "tools")
from zanackb.zanac_game import ZanacGame


def w(lo, hi):
    return lo | (hi << 8)


def main():
    seconds = float(sys.argv[1]) if len(sys.argv) > 1 else 120.0
    with ZanacGame.launch("source/zanac.rom") as game:
        msx = game.client
        msx.cmd("debug break")
        wbp = msx.cmd("debug set_bp 0x425A {} "
                      "{ debug write memory 0xE701 2; debug cont }")
        msx.cont()
        game.wait_for_title()
        game.start_game()
        time.sleep(1.0)
        try:
            game.make_invincible()
        except Exception:
            pass

        msx.cmd("set ::log {}")
        # spawn log
        lbp = msx.cmd(r"""debug set_bp 0x87C3 {} {
            set ix [reg IX]
            lappend ::log [list S [debug read memory $ix] \
                [debug read memory [expr {$ix+0x18}]] \
                [debug read memory [expr {$ix+0x03}]] \
                [debug read memory [expr {$ix+0x1c}]] \
                [debug read memory [expr {$ix+0x1d}]] \
                [debug read memory [expr {$ix+0x01}]] \
                [debug read memory [expr {$ix+0x02}]] \
                [debug read memory 0xE720] [debug read memory 0xE721] \
                [debug read memory 0xE704] [debug read memory 0xE705] \
                [debug read memory 0xE702] [debug read memory 0xE701]]
        }""")
        # E720 table-swap log (cmd 8 executions)
        wp = msx.cmd(r"""debug set_watchpoint write_mem 0xE721 {} {
            lappend ::log [list T [debug read memory 0xE720] $::wp_last_value \
                [debug read memory 0xE704] [debug read memory 0xE705] \
                [debug read memory 0xE702] [debug read memory 0xE701]]
        }""")
        msx.cmd("set throttle off")
        t0 = time.time()
        warped = "--warp" in sys.argv
        injected = False
        while time.time() - t0 < seconds:
            if not msx.is_running():
                msx.cont()
            time.sleep(0.5)
            if warped and not injected and time.time() - t0 > 2.0 \
                    and msx.read_byte(0xE701) == 2:
                # simulate touching the idx-4 black orb: warp to 0xAD4B.
                # E722 is also written by scroll code, so force it at the
                # consumer (0x40DD in level_complete_handler) instead.
                msx.cmd("debug break")
                msx.cmd("set ::wbp2 [debug set_bp 0x40DD {} { "
                        "debug write memory 0xE722 0x4B ; "
                        "debug write memory 0xE723 0xAD ; "
                        "debug remove_bp $::wbp2 }]")
                msx.write_byte(0xE102, msx.read_byte(0xE102) | 0x20)
                msx.cont()
                injected = True
                print("injected warp trigger", file=sys.stderr)
                continue
            if msx.read_byte(0xE701) not in (0, 2):
                break
        msx.cmd("set throttle on")
        raw = msx.cmd("set ::log")
        for h in (lbp, wp):
            try:
                msx.cmd("debug remove_bp " + h)
            except Exception:
                try:
                    msx.cmd("debug remove_watchpoint " + h)
                except Exception:
                    pass
        try:
            msx.cmd("debug remove_bp " + wbp)
        except Exception:
            pass

    # parse TCL list of brace-wrapped sublists
    out, depth, cur = [], 0, ""
    for ch in raw:
        if ch == "{":
            depth += 1
            if depth == 1:
                cur = ""
                continue
        elif ch == "}":
            depth -= 1
            if depth == 0:
                out.append(cur)
                continue
        if depth >= 1:
            cur += ch

    print(f"{len(out)} events")
    for tok in out:
        f = tok.split()
        tag = f[0]
        v = [int(x) for x in f[1:]]
        if tag == "T" and len(v) == 6:
            table = w(v[0], v[1])
            print(f"TABLE  E720={table:04X}  scriptPC={w(v[2], v[3]):04X} "
                  f"row={v[4]:3d} round={v[5]}")
        elif tag == "S" and len(v) == 13:
            typ, sub, idx = v[0], v[1], v[2]
            dest = w(v[3], v[4])
            y, x = v[5], v[6]
            table = w(v[7], v[8])
            pc = w(v[9], v[10])
            row, rnd = v[11], v[12]
            mark = "  <<< IDX-88" if idx == 88 else ""
            print(f"SPAWN  type={typ:3d} sub={sub:02X} idx={idx:3d} "
                  f"dest={dest:04X} Y={y:3d} X={x:3d} table={table:04X} "
                  f"scriptPC={pc:04X} row={row:3d} round={rnd}{mark}")


if __name__ == "__main__":
    main()
