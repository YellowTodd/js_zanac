# Controlling openMSX from Python

Reference for `tools/zanackb/openmsx.py` — the thin Python wrapper around the
openMSX external control protocol.  Everything here was learned by reading the
official docs at https://openmsx.org/manual/openmsx-control.html and the C++
example `openmsx-control-socket.cc` that ships with openMSX.

---

## 1. How the control interface works

### Launch

```bash
openmsx -control stdio -cart zanac.rom
```

The `-control stdio` flag does two things:

1. Uses the process's **stdin / stdout** as a control channel (reads TCL
   commands from stdin, writes XML replies to stdout).
2. Creates a **unix-domain socket** at
   `$TMPDIR/openmsx-<username>/socket.<pid>` that accepts the same protocol
   independently of stdin/stdout.

> **Headless mode.**  `-control stdio` forces the `none` renderer, so no
> window appears.  This is intentional for automated verification scripts.

> **`$TMPDIR` matters.**  openMSX uses the same temp-dir resolution as the
> C++ standard library: it checks `$TMPDIR`, `$TMP`, `$TEMP`, then falls back
> to `/tmp`.  In environments where `$TMPDIR` is set to something like
> `/tmp/claude-1000/`, the socket appears under that path, **not** under
> `/tmp/`.  The Python client mirrors this lookup.

### Wire protocol

All communication over the unix socket (or over stdio) is plain UTF-8 XML
with no length prefix.

**Handshake (connection startup)**

```
← <openmsx-output>          openMSX sends this immediately on connect
→ <openmsx-control>         client must send this immediately after connecting
```

Send `<openmsx-control>` right after connecting, *before* reading anything —
do not wait for `<openmsx-output>` to arrive first (the C++ example does the
same).

**Command / reply cycle**

```
→ <command>set renderer SDL</command>
← <reply result="ok">SDL</reply>

→ <command>biep</command>
← <reply result="nok">invalid command name "biep"</reply>
```

Commands are processed in order; replies arrive in the same order.  Between
replies, openMSX may emit `<log>` and `<update>` tags asynchronously — the
Python client discards these.

**Session end**

When openMSX exits it closes the socket and sends `</openmsx-output>`.  The
Python client raises `OpenMsxError("openMSX closed the connection")` on the
next read.

---

## 2. Keeping openMSX alive

openMSX exits when its **stdin reaches EOF**.  To keep it alive from Python
without deadlocking:

- Pass `stdin=subprocess.PIPE` to `Popen` — this keeps the write end of the
  pipe open.  Do **not** use `stdout=subprocess.PIPE` unless you actively
  drain it (pipe-full deadlock).
- Do **not** use `stdin=subprocess.DEVNULL` (`/dev/null`) — that gives
  immediate EOF and openMSX exits.
- Do **not** use `stdin` from `/dev/zero` — null bytes are not valid XML and
  corrupt the stdio control channel (the CPU will stall).

The `connect_subprocess()` factory handles all of this correctly.

---

## 3. Python API

### `OpenMsxClient`

```python
from zanackb.openmsx import OpenMsxClient, OpenMsxError, openmsx_session
```

#### Factory methods

| Method | Description |
|---|---|
| `OpenMsxClient.connect_subprocess(rom, extra_args, timeout)` | Launch `openmsx -control stdio [-cart rom]`, wait for the socket, connect. Returns `(client, proc)`. Caller must call `proc.terminate()`. |
| `OpenMsxClient.autoconnect()` | Connect to the most-recently modified socket in `$TMPDIR/openmsx-<user>/`. Requires openMSX to already be running. |
| `OpenMsxClient.connect_unix(path, timeout)` | Connect to a specific socket path. |

#### Context manager

```python
# Start a fresh openMSX instance, connect, then clean up automatically:
with openmsx_session(rom="source/zanac.rom") as msx:
    ver = msx.cmd("openmsx_info version")

# Attach to an already-running instance:
with openmsx_session() as msx:
    ...
```

#### Methods

| Method | TCL sent | Description |
|---|---|---|
| `cmd(tcl)` | `<command>tcl</command>` | Run any TCL command, return result string. Raises `OpenMsxError` on `nok`. |
| `read_memory(addr, n)` | `binary scan [debug read_block memory addr n] H* h; set h` | Read *n* CPU-space bytes as `bytes`. |
| `read_debuggable(name, offset, n)` | `binary scan [debug read_block {name} offset n] H* h; set h` | Read from a named openMSX debuggable. |
| `write_memory(addr, data)` | `debug write memory addr byte` × n | Write bytes to CPU address space. |
| `set_breakpoint(addr, tcl_action)` | `debug set_bp addr true {action}` | Register breakpoint; return `bp#N` id. |
| `remove_breakpoint(bp_id)` | `debug remove_bp bp_id` | Remove a breakpoint by id. |
| `power_on()` | `set power on` | Power the MSX on. **Required before the CPU will run.** |
| `step()` | `debug step` | Execute one instruction (CPU must be paused). |
| `cont()` | `debug cont` | Resume execution. |
| `reset()` | `reset` | Reset the MSX (CPU and hardware). |
| `close()` | — | Close the socket. |

---

## 4. Critical gotchas

### The machine starts powered off

After connecting, the MSX is in a **powered-off** state.  The CPU will not
execute instructions until you call `power_on()`.  Calling `cont()` or
`reset()` without `power_on()` has no effect on PC or R.

```python
client, proc = OpenMsxClient.connect_subprocess(rom=ROM)
client.power_on()   # <-- without this, CPU never runs
client.cont()
```

### Raw binary from `debug read_block` corrupts XML

The TCL `debug read_block memory addr n` command returns raw binary bytes
embedded directly in the XML reply body.  Non-ASCII bytes break UTF-8
decoding and corrupt the XML parser.

**Always use `binary scan` to convert to hex first:**

```python
# WRONG — raw binary may contain bytes that break XML:
raw = msx.cmd("debug read_block memory 0x4000 16")

# CORRECT — hex string is always XML-safe:
hex_str = msx.cmd("binary scan [debug read_block memory 0x4000 16] H* h; set h")
data = bytes.fromhex(hex_str)
```

`read_memory()` and `read_debuggable()` apply this fix automatically.

### Reading ROM content via the debuggable, not CPU address space

At boot, the MSX BIOS occupies page 1 (0x4000–0x7FFF) in the CPU address
space.  The cartridge ROM is only mapped there once the BIOS detects it and
calls its INIT entry point.  To read the ROM content before the BIOS maps it,
use the named debuggable:

```python
# Insert the cart (if not passed as -cart at launch):
msx.cmd("carta /path/to/zanac.rom")

# Read 16 bytes from offset 0 of the ROM (= address 0x4000 in the ROM):
header = msx.read_debuggable("Zanac A.I.", 0, 16)
```

The debuggable name (`"Zanac A.I."`) is the ROM's internal name as reported
by `debug list`.

### Registers via `reg`, not `debug read_block {CPU regs}`

`debug read_block {CPU regs}` returns a 28-byte binary blob whose layout does
not straightforwardly map to the obvious register order.  Use the `reg`
command instead:

```python
pc = int(msx.cmd("reg PC"))   # program counter
sp = int(msx.cmd("reg SP"))   # stack pointer
r  = int(msx.cmd("reg R"))    # refresh register — increments each fetch
a  = int(msx.cmd("reg A"))
```

Available register names: `PC`, `SP`, `AF`, `A`, `F`, `BC`, `BC`, `DE`,
`HL`, `IX`, `IY`, `I`, `R`, `A2`, `F2` (alternate registers).

### Breakpoint actions run asynchronously

A breakpoint action TCL script executes inside openMSX's own thread when the
CPU hits the address.  The control client never sees a notification that the
BP fired — it only sees replies to commands it explicitly sends.

To detect a BP hit, store a flag in a TCL global variable and poll it:

```python
msx.cmd("set ::my_flag 0")
bp = msx.set_breakpoint(0x4010, "set ::my_flag 1; debug break")
msx.cont()
time.sleep(3)
hit = msx.cmd("set ::my_flag")   # "1" if hit, "0" if not
```

`debug break` inside the action **pauses the CPU** — without it the CPU
continues running past the breakpoint.

---

## 5. Common TCL recipes

All of these can be passed to `msx.cmd(...)`.

### Version

```tcl
openmsx_info version
```

### List all debuggables (ROMs, RAM, VDP, CPU regs, PSG regs, …)

```tcl
debug list
```

### Read CPU address space (hex, safe for XML)

```tcl
binary scan [debug read_block memory 0x4000 16] H* h; set h
```

### Read a specific debuggable

```tcl
binary scan [debug read_block {Zanac A.I.} 0 16] H* h; set h
```

### Read a single CPU-space byte (returned as decimal)

```tcl
debug read memory 0x4000
```

### Read a register

```tcl
reg PC
reg R
```

### Write a single byte

```tcl
debug write memory 0xC000 0x42
```

### Set a breakpoint (always fires, no action)

```tcl
debug set_bp 0x4010 true {}
```

### Set a breakpoint with an action that pauses execution

```tcl
debug set_bp 0x4010 true {set ::hit 1; debug break}
```

### Set a conditional breakpoint (only when A == 0xFF)

```tcl
debug set_bp 0x4010 {[reg A] == 255} {set ::hit 1; debug break}
```

### List all active breakpoints

```tcl
debug list_bp
```

### Remove a breakpoint

```tcl
debug remove_bp bp#1
```

### Set a write watchpoint on an I/O port (e.g. PSG register select)

```tcl
debug set_watchpoint write_io 0xA0 {} {set ::psg_reg [reg A]; debug break}
```

### Single step (CPU must be paused)

```tcl
debug step
```

### Continue execution

```tcl
debug cont
```

### Reset the machine

```tcl
reset
```

### Power the machine on

```tcl
set power on
```

### Insert a cartridge

```tcl
carta /path/to/rom
```

---

## 6. Complete example: verify cold_start is reached

```python
import time
from zanackb.openmsx import OpenMsxClient, OpenMsxError, openmsx_session

ROM = "source/zanac.rom"

with openmsx_session(rom=ROM) as msx:
    # 1. Confirm the ROM header
    header = msx.read_debuggable("Zanac A.I.", 0, 16)
    magic     = header[0:2]
    init_addr = header[2] | (header[3] << 8)
    assert magic == b'AB', f"bad magic: {magic.hex()}"
    assert init_addr == 0x4010, f"unexpected INIT: 0x{init_addr:04X}"
    print(f"ROM header OK: magic=AB, INIT=0x{init_addr:04X}")

    # 2. Power on and set a breakpoint at cold_start
    msx.cmd("set ::cold_start_hit 0")
    bp = msx.set_breakpoint(0x4010, "set ::cold_start_hit 1; debug break")

    msx.power_on()
    time.sleep(4)   # give the BIOS time to detect and call the cart INIT

    hit = msx.cmd("set ::cold_start_hit")
    if hit == "1":
        pc = int(msx.cmd("reg PC"))
        print(f"cold_start reached: PC=0x{pc:04X}")   # should be 0x4010
    else:
        print("cold_start NOT reached within 4s")

    msx.remove_breakpoint(bp)
```

---

## 7. Troubleshooting

| Symptom | Likely cause | Fix |
|---|---|---|
| `OpenMsxError: no openMSX socket directory` | openMSX not running, or socket in wrong dir | Check `$TMPDIR`; look for `socket.*` under `$TMPDIR/openmsx-<user>/` |
| `OpenMsxError: openMSX did not create a socket within Ns` | Process exited before socket appeared | Check process exit code; confirm `-control stdio` flag is present |
| Socket exists but `_read_until` hangs forever | Old/stale socket file from a dead process | Delete the stale socket; openMSX will create a fresh one on next launch |
| CPU registers never change after `cont()` | Machine is powered off | Call `power_on()` before `cont()` |
| `read_memory` returns garbage / raises `ValueError` | Raw binary from `debug read_block` | Use `read_memory()` / `read_debuggable()` which apply `binary scan` |
| Breakpoint set but `::my_flag` stays 0 | BIOS hasn't mapped cart yet, or BP address wrong | Set BP **before** `power_on()` to avoid race; BIOS takes ~2s to call cart INIT at 0x4010 |
| `reg SP` raises error in BP action | Register name differs | Use `reg SP` not `reg sp`; check valid names with `info commands reg` |
| `pkill -f openmsx` hangs the shell | `-f` matches the shell's own command line | Use `pkill openmsx` (name-only, no `-f`) |
| `OpenMsxError: Unknown subcommand 'running'` | `debug running` does not exist | Use `debug breaked` instead (returns "1" = paused, "0" = running) |
| `cont()` on running CPU has no effect | CPU is already running, `debug cont` is a no-op | Check `debug breaked` == "1" before calling `cont()` |

---

## 8. Zanac-specific: screen-state detection

The most reliable way to detect Zanac's game phase is to read the **VRAM name
table at 0x3800** and check for ASCII text strings (tile codes match ASCII
for all text characters in this game):

```python
raw = client.read_debuggable("VRAM", 0x3800, 0x300)
text = "".join(chr(b) if 0x20 <= b < 0x7F else " " for b in raw)

if "COMPILE"   in text: phase = "title"
elif "PAUSE"   in text: phase = "paused"
elif "GAME OVER" in text: phase = "game_over"
elif "ZANAC"   in text: phase = "in_game"
else:                     phase = "unknown"
```

`read_name_table()` on `OpenMsxClient` does this automatically.

**Note:** `E102` (game flags) is 0x00 in ALL phases — it is NOT a reliable
phase discriminator. Text detection is the correct approach.

---

## 9. Zanac-specific: keyboard injection

`keymatrixdown row mask` / `keymatrixup row mask` write directly to the virtual
MSX matrix, bypassing physical keyboard mapping. For Zanac (confirmed from
source analysis):

| Key | Row | Mask | Purpose |
|---|---|---|---|
| SPACE (title) | 7 | 0x04 | `check_esc_key` reads row 7 bit 2 |
| SPACE (gameplay) | 8 | 0x01 | movement handler reads row 8 bit 0 |
| ↑ UP | 8 | 0x20 | |
| ↓ DOWN | 8 | 0x40 | |
| ← LEFT | 8 | 0x10 | |
| → RIGHT | 8 | 0x80 | |
| SHIFT (shot) | 6 | 0x01 | |
| Z (fire weapon) | 5 | 0x80 | |
| STOP (pause) | 7 | 0x10 | |

Inject SPACE on **both** rows (7 and 8) for reliable title-screen start.
Hold each key ~100ms, then release and check screen state.

---

## 10. Complete example: autonomous Zanac game loop

```python
from zanackb.zanac_game import ZanacGame

with ZanacGame.launch("source/zanac.rom") as game:
    # 1. Wait for title screen (~1s from power-on)
    game.wait_for_title()

    # 2. Start game
    game.start_game()

    # 3. Arm event detectors
    game.arm_collision_detector()
    game.arm_kill_detector()

    # 4. Play: move up and shoot
    game.steer(up=True)
    game.shoot_both()

    # 5. Detect events
    if game.wait_for_collision(timeout=10):
        print(f"Hit! Lives remaining: {game.lives()}")

    # 6. Wait for game over
    game.wait_for_game_over(timeout=60)

    # 7. Return to title
    game.skip_to_title()
```

---

## 11. PNG screenshots (visual verification)

`ZanacGame.launch()` / `OpenMsxClient.connect_subprocess()` pass
**`-control stdio`**, which forces openMSX into headless mode
(`renderer = none`). In that mode `screenshot` fails with *"Taking screenshot
not possible with current renderer."* — so the standard launch path **cannot**
take screenshots.

To capture real frames (background, sprites, logo — everything the player
sees), launch openMSX **without** `-control stdio`. A normal launch:

1. Opens an SDL window on `$DISPLAY` (a real X display must exist — `echo
   $DISPLAY` should print e.g. `:0`).
2. Still creates a control socket at `/tmp/openmsx-<user>/socket.<pid>`, which
   you connect to with `OpenMsxClient.connect_unix(sock)`.
3. Uses the renderer from settings (default `SDLGL-PP`), which **does** support
   `screenshot`.

> `-renderer` is **not** a valid command-line flag in this build — the launch
> aborts with *"Error parsing command line: -renderer"*. Renderer comes from
> settings; override at runtime with `set renderer SDLGL-PP` if needed.

The machine auto-powers-on on a normal launch (no need to set the cold_start BP
before `power_on()` as the stdio path does). Take the shot with:

```python
msx.cmd(f"screenshot {abs_path}.png")   # writes a PNG; SDLGL-PP only
```

Then view it with the agent's `Read` tool (it renders PNGs visually).

### Helper: `tools/zanac_shot.py`

`ShotSession` wraps the whole dance (background launch → find new socket →
connect → screenshot):

```python
from zanac_shot import ShotSession          # tools/ on sys.path

with ShotSession(savestate="savestates/game-end.oms") as s:
    s.run(3.0)                               # let frames render
    s.shot("/tmp/frame.png")                 # -> PNG, view with Read

# Fresh boot + drive the game, then shoot:
from zanackb.zanac_game import ZanacGame
with ShotSession() as s:
    game = ZanacGame(s.msx)
    game.wait_for_title(); game.start_game()
    s.shot("/tmp/gameplay.png")
```

`ShotSession` records `/tmp/openmsx-<user>/socket.*` *before* spawning, then
picks the newly-created socket containing its own PID — so it is safe to run
even while other openMSX instances are alive.

**Gotcha:** the window appears on the user's live display. Keep sessions short
and always exit the context manager (it terminates the process).

