"""Sprint 0027 — game_state_block gap fill (0xE100–0xE14F).

Phase 1: snapshots at title / game_start / mid_game /
         base_approach / base_active / post_base.
         Uses warp(5) + make_invincible() to reach a base within ~90 s.

Phase 2: write-watchpoints (no CPU break) for all unknown changing bytes;
         context read happens in the same session while ROM is mapped.
"""

import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from zanackb.zanac_game import ZanacGame

BASE  = 0xE100
SIZE  = 80

# ── known fields ──────────────────────────────────────────────────────────────
NAMED = {
    0xE100: "input_state",          # joystick+keyboard bitmask, updated each frame
    0xE102: "status_flags",
    0xE103: "score_lo",
    0xE104: "score_mid",
    0xE105: "score_hi",
    0xE106: "topscore_lo",
    0xE107: "topscore_mid",
    0xE108: "topscore_hi",
    0xE10A: "lives",
    0xE10B: "shot_level",
    0xE10C: "player_x_vel",         # from keyboard-input.md: base 4 ±dirs
    0xE10D: "shot_max_simultaneous",
    0xE10E: "shot_vy_raw",
    0xE10F: "shot_sat_name",
    0xE110: "round",
    0xE125: "spawn_trigger",
    0xE126: "stream_slot_ctr",
    0xE12D: "spawn_ctrl",
    0xE12E: "spawn_pos_hi",
    0xE12F: "spawn_pos_lo",
    0xE130: "base_health_ctr",
    0xE132: "scroll_offset",
    0xE133: "spawn_table_ptr",
    0xE134: "spawn_table_ptr+1",
    0xE135: "spawn_subtable_ctr",
    0xE137: "spawn_timer",
    0xE138: "spawn_timer_reload",
    0xE142: "spawn_event_ctr",
    0xE147: "fire_debounce",        # from keyboard-input.md: sub_46bc edge detect
    0xE14B: "fire_type",
    0xE14C: "fire_limit_1",
    0xE14D: "fire_counter",
    0xE14E: "fire_limit_3",
}


def snap(msx) -> bytes:
    return bytes(msx.read_memory(BASE, SIZE))


def print_hex(label: str, data: bytes):
    print(f"\n  [{label}]")
    for i in range(0, SIZE, 16):
        chunk = data[i:i+16]
        addr  = BASE + i
        print(f"    {addr:04X}: {' '.join(f'{b:02X}' for b in chunk)}")


def wait_for_base(msx, timeout: float = 150.0) -> bool:
    """Poll until current_scroll_speed (0xE710) drops below 0x20.
    Prints progress every 10 s."""
    deadline = time.time() + timeout
    last_report = time.time()
    while time.time() < deadline:
        speed  = msx.read_byte(0xE710)
        target = msx.read_byte(0xE712)
        flags  = msx.read_byte(0xE150)
        if time.time() - last_report >= 10.0:
            print(f"    scroll_speed=0x{speed:02X}  target=0x{target:02X}"
                  f"  base_flags=0x{flags:02X}")
            last_report = time.time()
        if speed < 0x20:
            return True
        time.sleep(0.15)
    return False


def wait_for_base_cleared(msx, timeout: float = 60.0) -> bool:
    """After base fight, poll until scroll restarts (speed > 0x10)."""
    deadline = time.time() + timeout
    while time.time() < deadline:
        speed = msx.read_byte(0xE710)
        if speed > 0x10:
            return True
        time.sleep(0.15)
    return False


# ── Phase 1 ───────────────────────────────────────────────────────────────────

def phase1_snapshots() -> tuple[dict[str, bytes], list[int]]:
    print("=" * 60)
    print("PHASE 1 — snapshots across game phases (warp 5, invincible)")
    print("=" * 60)

    snapshots: dict[str, bytes] = {}

    with ZanacGame.launch() as game:
        msx = game.client

        # Arm warp BEFORE start so it fires when SPACE is pressed
        game.arm_warp(5)

        print("\nWaiting for title...")
        game.wait_for_title()
        snapshots["title"] = snap(msx)
        print_hex("title", snapshots["title"])

        print("\nStarting game (warp to round 5)...")
        game.start_game()
        game.make_invincible()
        time.sleep(1.0)
        snapshots["game_start"] = snap(msx)
        print_hex("game_start", snapshots["game_start"])
        print(f"  scroll_speed=0x{msx.read_byte(0xE710):02X}  "
              f"round={msx.read_byte(0xE110):02X}")

        print("\nWaiting 8 s for mid-game snapshot...")
        time.sleep(8.0)
        snapshots["mid_game"] = snap(msx)
        print_hex("mid_game", snapshots["mid_game"])

        print("\nWaiting for base approach (scroll_speed < 0x20)...")
        reached = wait_for_base(msx, timeout=150.0)
        if reached:
            # Capture deceleration snapshot
            snapshots["base_approach"] = snap(msx)
            print_hex("base_approach", snapshots["base_approach"])
            speed = msx.read_byte(0xE710)
            flags = msx.read_byte(0xE150)
            print(f"  scroll_speed=0x{speed:02X}  base_flags=0x{flags:02X}")

            # Wait for full stop (speed == 0 or base_flags non-zero)
            for _ in range(60):
                speed  = msx.read_byte(0xE710)
                flags  = msx.read_byte(0xE150)
                if speed == 0 or (flags & 0x03):
                    break
                time.sleep(0.25)
            snapshots["base_active"] = snap(msx)
            print_hex("base_active", snapshots["base_active"])
            print(f"  scroll_speed=0x{speed:02X}  base_flags=0x{flags:02X}")

            print("\nWaiting for base to be destroyed (scroll restarts)...")
            cleared = wait_for_base_cleared(msx, timeout=60.0)
            if cleared:
                snapshots["post_base"] = snap(msx)
                print_hex("post_base", snapshots["post_base"])
                print(f"  scroll_speed=0x{msx.read_byte(0xE710):02X}")
            else:
                print("  (base not destroyed within 60 s)")
        else:
            print("  (base not reached within 150 s)")

    # ── change table ──────────────────────────────────────────────────────────
    print("\n" + "=" * 60)
    print("CHANGE TABLE — bytes that differ across any phase")
    print("=" * 60)
    ph_names = list(snapshots.keys())
    hdr = "  " + f"{'Addr':6s}  {'off':5s}  {'name':28s}  " + \
          "  ".join(f"{ph[:9]:9s}" for ph in ph_names)
    print(hdr)
    print()

    changing_unknown: list[int] = []
    for off in range(SIZE):
        addr = BASE + off
        vals = [data[off] for data in snapshots.values()]
        if len(set(vals)) == 1:
            continue
        name  = NAMED.get(addr, "?")
        cells = "  ".join(f"{v:02X}       " for v in vals)
        print(f"  0x{addr:04X}  +0x{off:02X}  {name:28s}  {cells}")
        if name == "?":
            changing_unknown.append(addr)

    # ── stable unknown table ──────────────────────────────────────────────────
    print("\n" + "=" * 60)
    print("STABLE UNKNOWNS — never-changing unnamed bytes")
    print("=" * 60)
    ref = list(snapshots.values())[1] if len(snapshots) > 1 else list(snapshots.values())[0]
    for off in range(SIZE):
        addr = BASE + off
        vals = [data[off] for data in snapshots.values()]
        if len(set(vals)) > 1:
            continue
        if NAMED.get(addr):
            continue
        print(f"  0x{addr:04X} +0x{off:02X}  val={vals[0]:02X}")

    return snapshots, changing_unknown


# ── Phase 2 ───────────────────────────────────────────────────────────────────

def phase2_watchpoints(changing_unknown: list[int]):
    if not changing_unknown:
        print("\nNo unknown changing bytes — skipping watchpoint phase.")
        return

    print("\n" + "=" * 60)
    print("PHASE 2 — write-watchpoints (no CPU break)")
    print("=" * 60)
    print(f"  {len(changing_unknown)} targets: "
          + ", ".join(f"0x{a:04X}" for a in changing_unknown))

    BATCH = 16  # arm all at once — no CPU break so no interference
    results: dict[int, int] = {}

    with ZanacGame.launch() as game:
        msx = game.client
        game.arm_warp(5)

        # Arm all watchpoints before game starts — no debug break, just record PC
        for addr in changing_unknown:
            var = f"wp_pc_{addr:04X}"
            msx.cmd(f"set ::{var} 0")
            msx.cmd(
                f"debug set_watchpoint write_mem 0x{addr:04X} {{}} "
                f"{{set ::{var} [reg PC]}}"
            )

        print("\n  Waiting for title...")
        game.wait_for_title()
        game.start_game()
        game.make_invincible()

        print("  Running 10 s of gameplay (round 5)...")
        time.sleep(10.0)

        # Collect PCs
        for addr in changing_unknown:
            var = f"wp_pc_{addr:04X}"
            raw = msx.cmd(f"set ::{var}")
            try:
                pc = int(raw.strip(), 16) if raw.strip() not in ("0", "") else 0
            except ValueError:
                pc = 0
            results[addr] = pc

        # Read context in the same session (ROM mapped at correct addresses)
        print("\n" + "=" * 60)
        print("WRITER PC REPORT")
        print("=" * 60)
        print(f"  {'Addr':6s}  {'PC':6s}  {'context [-4..0]':36s}  instruction")
        print()
        for addr, pc in sorted(results.items()):
            if pc == 0:
                print(f"  0x{addr:04X}  ------  (no write observed)")
                continue
            # Read 8 bytes ending at pc to capture the writing instruction
            ctx_start = max(0x4000, pc - 4)
            ctx_len   = pc - ctx_start + 1
            try:
                ctx  = bytes(msx.read_memory(ctx_start, ctx_len))
                hex_ = " ".join(f"{b:02X}" for b in ctx)
                # Identify last 1-2 bytes as the likely instruction
                instr = _decode_last_instr(ctx, ctx_start, pc)
                print(f"  0x{addr:04X}  {pc:04X}  [{ctx_start:04X}] {hex_:34s}  {instr}")
            except Exception as exc:
                print(f"  0x{addr:04X}  {pc:04X}  (context error: {exc})")


def _decode_last_instr(ctx: bytes, base_addr: int, pc: int) -> str:
    """Best-effort decode of the Z80 instruction ending at pc."""
    if not ctx:
        return "?"
    b = ctx[-1]
    # Common Z80 writes: LD (IX+d),r; LD (HL),A; LD (nn),A; INC/DEC (IX+d)
    if len(ctx) >= 3 and ctx[-3] == 0xDD:
        d  = ctx[-2]
        op = ctx[-1]
        regs = {0x70:'B',0x71:'C',0x72:'D',0x73:'E',0x74:'H',0x75:'L',0x77:'A'}
        if op in regs:
            offset = d if d < 128 else d - 256
            return f"LD (IX{offset:+d}), {regs[op]}"
        if op == 0x35:
            offset = d if d < 128 else d - 256
            return f"DEC (IX{offset:+d})"
        if op == 0x34:
            offset = d if d < 128 else d - 256
            return f"INC (IX{offset:+d})"
    if b == 0x77:
        return "LD (HL), A"
    if b == 0x32 and len(ctx) >= 3:
        nn = ctx[-3] | (ctx[-2] << 8)
        return f"LD (0x{nn:04X}), A"
    if b == 0x36:
        return "LD (HL), n"
    if len(ctx) >= 2 and ctx[-2] == 0xFD:
        # IY-indexed
        return f"IY-indexed op 0x{b:02X}"
    return f"op 0x{b:02X}"


# ── main ──────────────────────────────────────────────────────────────────────

def main():
    snapshots, changing_unknown = phase1_snapshots()
    phase2_watchpoints(changing_unknown)
    print("\nDone.")


if __name__ == "__main__":
    main()
