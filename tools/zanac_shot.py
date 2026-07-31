"""Launch openMSX with a real renderer and grab PNG screenshots.

Unlike ZanacGame.launch (which uses -control stdio -> renderer=none, no
screenshots), this starts openMSX normally so it creates a control socket we
can autoconnect to, and the SDL renderer supports `screenshot`.

Usage:
    from zanac_shot import ShotSession
    with ShotSession(savestate="savestates/game-end.oms") as s:
        s.run(3.0)
        s.shot("/tmp/a.png")
"""
import os, subprocess, sys, time, glob
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from zanackb.openmsx import OpenMsxClient

ROM = os.path.abspath("source/zanac.rom")


class ShotSession:
    def __init__(self, savestate=None, rom=ROM):
        args = ["openmsx", "-cart", rom]
        if savestate:
            args += ["-savestate", os.path.abspath(savestate)]
        # clear stale sockets
        self._before = set(glob.glob("/tmp/openmsx-mgm/socket.*"))
        self.proc = subprocess.Popen(args, stdout=subprocess.DEVNULL,
                                     stderr=subprocess.DEVNULL)
        self.msx = None

    def __enter__(self):
        sock = None
        for _ in range(40):
            time.sleep(0.5)
            cur = set(glob.glob("/tmp/openmsx-mgm/socket.*"))
            new = cur - self._before
            cand = [s for s in new if str(self.proc.pid) in s] or list(new)
            if cand:
                sock = cand[0]
                break
        if not sock:
            self.proc.terminate()
            raise RuntimeError("no socket")
        time.sleep(0.5)
        self.msx = OpenMsxClient.connect_unix(sock)
        # default renderer in settings supports screenshot; make sure running
        try:
            if not self.msx.is_running():
                self.msx.cont()
        except Exception:
            pass
        return self

    def cmd(self, c):
        return self.msx.cmd(c)

    def run(self, secs):
        time.sleep(secs)

    def shot(self, path):
        path = os.path.abspath(path)
        self.msx.cmd(f"screenshot -prefix {{}} {path}")
        return path

    def __exit__(self, *a):
        try:
            self.proc.terminate(); self.proc.wait(timeout=5)
        except Exception:
            self.proc.kill()


if __name__ == "__main__":
    out = sys.argv[1] if len(sys.argv) > 1 else "/tmp/zanac_ref.png"
    with ShotSession(savestate="savestates/game-end.oms") as s:
        print("renderer:", s.cmd("set renderer"))
        s.run(3.0)
        p = s.shot(out)
        time.sleep(0.5)
        print("saved:", p, os.path.exists(p), os.path.getsize(p) if os.path.exists(p) else "-")
