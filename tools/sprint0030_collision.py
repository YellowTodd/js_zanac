"""Sprint 0030 — Collision detection system (0x4560–0x4648).

Steps:
  1. Disassemble 0x4560 routine via openMSX debug disasm.
  2. Read and print the collision class table at 0x716B (90 bytes).
  3. Identify and print the collision matrix from the disassembly.
  4. Live verification: breakpoint at 0x453E to catch a collision event.
"""

import subprocess
import sys
import tempfile
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from zanackb.openmsx import MSXKey
from zanackb.zanac_game import ZanacGame

ROM = "source/zanac.rom"

ROUTINE_START = 0x4560
ROUTINE_END   = 0x4649   # exclusive upper bound (sprint range 0x4560–0x4648)
CLASS_TABLE   = 0x716B
CLASS_TABLE_N = 90       # entity types 0–89


# ── helpers ───────────────────────────────────────────────────────────────────

def disasm_z80dasm(data: bytes, origin: int) -> str:
    """Disassemble binary data with z80dasm, origin sets the base address."""
    with tempfile.NamedTemporaryFile(suffix=".bin", delete=False) as f:
        f.write(data)
        tmp = f.name
    result = subprocess.run(
        ["z80dasm", f"--origin={origin}", "--address", "--source", tmp],
        capture_output=True, text=True,
    )
    Path(tmp).unlink(missing_ok=True)
    return result.stdout


# ── Step 1: disassemble the collision routine ─────────────────────────────────

def step1_disasm(msx):
    print("=" * 64)
    print("STEP 1 — Disassembly of collision_routine (0x4560–0x4648)")
    print("=" * 64)

    size = ROUTINE_END - ROUTINE_START
    raw = bytes(msx.read_memory(ROUTINE_START, size))

    print(f"Raw bytes ({size} bytes from 0x{ROUTINE_START:04X}):")
    for i in range(0, size, 16):
        chunk = raw[i:i+16]
        print(f"  {ROUTINE_START+i:04X}: {' '.join(f'{b:02X}' for b in chunk)}")

    print()
    print("Disassembly (z80dasm):")
    asm = disasm_z80dasm(raw, ROUTINE_START)
    print(asm)
    return raw


# ── Step 2: collision class table ─────────────────────────────────────────────

def step2_class_table(msx):
    print()
    print("=" * 64)
    print(f"STEP 2 — Collision class table at 0x{CLASS_TABLE:04X} ({CLASS_TABLE_N} bytes)")
    print("=" * 64)

    data = bytes(msx.read_memory(CLASS_TABLE, CLASS_TABLE_N))

    print("Raw bytes:")
    for i in range(0, CLASS_TABLE_N, 16):
        chunk = data[i:i+16]
        print(f"  {CLASS_TABLE+i:04X}: {' '.join(f'{b:02X}' for b in chunk)}")

    print()
    print("Non-zero entries (entity type → collision class):")
    by_class: dict[int, list[int]] = {}
    for typ in range(CLASS_TABLE_N):
        cls = data[typ]
        if cls != 0:
            by_class.setdefault(cls, []).append(typ)
            print(f"  type {typ:2d} (0x{typ:02X}) → class {cls}")

    print()
    print("By class:")
    for cls in sorted(by_class):
        types = ", ".join(f"{t}" for t in by_class[cls])
        print(f"  class {cls}: types [{types}]")

    return data


# ── Step 3: locate and print any embedded matrix ──────────────────────────────

def step3_matrix(msx, raw: bytes):
    print()
    print("=" * 64)
    print("STEP 3 — Collision matrix: scan LD HL,nn refs in routine")
    print("=" * 64)

    # Scan raw bytes for LD HL,nn (opcode 0x21 nn lo nn hi) patterns
    table_refs: list[int] = []
    for i in range(len(raw) - 2):
        if raw[i] == 0x21:
            ref = raw[i+1] | (raw[i+2] << 8)
            addr = ROUTINE_START + i
            print(f"  {addr:04X}: LD HL,0x{ref:04X}  → possible table")
            table_refs.append(ref)

    print()
    for ref in table_refs:
        data = bytes(msx.read_memory(ref, 32))
        hex_str = " ".join(f"{b:02X}" for b in data)
        print(f"  [0x{ref:04X}] +00: {hex_str[:23]}")
        print(f"  [0x{ref:04X}] +16: {' '.join(f'{b:02X}' for b in data[16:])}")


# ── Step 4: live collision verification ───────────────────────────────────────

def step4_live(game):
    msx = game.client
    print()
    print("=" * 64)
    print("STEP 4 — Live collision verification")
    print("=" * 64)

    print("  Waiting for title screen...")
    if not game.wait_for_title(timeout=30.0):
        print("  Title screen not detected within 30 s — aborting step 4.")
        return
    print(f"  Title detected. Starting game...")
    if not game.start_game(timeout=20.0):
        print("  Could not start game — aborting step 4.")
        return
    print(f"  In-game confirmed (screen={game.screen_state()}).")

    print(f"  In-game. Giving enemies 3 s to spawn...")
    time.sleep(3.0)

    # Set BP only after gameplay is confirmed; avoids spurious title-screen fires.
    # 0x453E is the tail-path of entity_post reached when entity_clear is called
    # after a confirmed collision (also reached on "skip collision" path, so we
    # capture the first event that has an entity pair in IX/IY).
    msx.cmd("set ::collision_fired 0")
    bp = msx.set_breakpoint(
        0x453E,
        "set ::collision_fired 1; debug break"
    )

    # Steer up toward incoming enemies and hold SHIFT to shoot continuously
    game.steer(up=True)
    game.shoot_shot()

    print("  Playing: steering up + shooting, waiting up to 30 s for collision...")
    deadline = time.time() + 30.0
    fired = False
    while time.time() < deadline:
        time.sleep(0.3)
        flag = msx.cmd("set ::collision_fired")
        if flag.strip() == "1":
            fired = True
            break

    # Stop player inputs
    game.steer()
    game.release_shot()

    if not fired:
        msx.remove_breakpoint(bp)
        print("  No collision detected within 30 s.")
        return

    # CPU is paused at 0x453E — read registers directly while paused
    # CPU is paused — reg returns decimal integers
    ix  = int(msx.cmd("reg IX"))
    iy  = int(msx.cmd("reg IY"))
    pc  = int(msx.cmd("reg PC"))

    ix_slot = bytes(msx.read_memory(ix, 32))
    iy_slot = bytes(msx.read_memory(iy, 32))

    ix_type = ix_slot[0] & 0x7F
    iy_type = iy_slot[0] & 0x7F
    ix_col  = ix_slot[0x18]
    iy_col  = iy_slot[0x18]

    print(f"  Collision fired! PC=0x{pc:04X}")
    print(f"  IX=0x{ix:04X}  type={ix_type} (0x{ix_type:02X})  col_type_cache={ix_col}")
    print(f"  IY=0x{iy:04X}  type={iy_type} (0x{iy_type:02X})  col_type_cache={iy_col}")
    print(f"  IX slot: {' '.join(f'{b:02X}' for b in ix_slot)}")
    print(f"  IY slot: {' '.join(f'{b:02X}' for b in iy_slot)}")

    msx.remove_breakpoint(bp)
    msx.cont()


# ── main ──────────────────────────────────────────────────────────────────────

def main():
    print("Launching openMSX...")
    with ZanacGame.launch(ROM) as game:
        msx = game.client

        raw = step1_disasm(msx)
        step2_class_table(msx)
        step3_matrix(msx, raw)
        step4_live(game)

    print("\nDone.")


if __name__ == "__main__":
    main()
