"""Sprint 0021 — Entity slot field capture.

Runs a 200-frame capture at entity_dispatch (0x445F) and dumps per-slot bytes
for types 1, 2, 39, and 44 so we can correlate frame-to-frame changes with
field semantics.
"""

import sys
import time
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from zanackb.zanac_game import ZanacGame

ENTITY_BASE   = 0xE300
SLOT_SIZE     = 32
NUM_SLOTS     = 26
TABLE_SIZE    = NUM_SLOTS * SLOT_SIZE  # 832 bytes

TARGET_TYPES  = {1, 2, 39, 44}
BP_ADDR       = 0x445F   # entity_dispatch entry

SAMPLE_EVERY  = 10  # take a snapshot every 10 dispatch calls
NUM_SAMPLES   = 20  # 20 × 10 = 200 frames


def parse_slots(raw: bytes) -> list[tuple[int, bytes]]:
    """Return [(type_id, 32_bytes), ...] for all active slots."""
    slots = []
    for i in range(NUM_SLOTS):
        slot = raw[i * SLOT_SIZE : (i + 1) * SLOT_SIZE]
        type_id = slot[0] & 0x7F  # strip bit-7 (active flag)
        slots.append((type_id, slot))
    return slots


def hex_row(data: bytes, start: int = 0) -> str:
    return " ".join(f"{b:02X}" for b in data[start:start+32])


def main():
    print("Launching openMSX...")
    with ZanacGame.launch() as game:
        msx = game.client

        print("Waiting for title screen...")
        game.wait_for_title()
        time.sleep(0.5)

        print("Starting game...")
        game.start_game()
        time.sleep(2.0)

        # Steer up and shoot to get enemies to spawn
        game.steer(up=True)
        game.shoot_shot()
        time.sleep(0.5)

        # --- frame capture ---
        print(f"Installing breakpoint at 0x{BP_ADDR:04X}...")
        msx.cmd("set ::dispatch_count 0")
        bp = msx.set_breakpoint(
            BP_ADDR,
            f"incr ::dispatch_count; "
            f"if {{$::dispatch_count % {SAMPLE_EVERY} == 0}} {{debug break}}"
        )

        # per_type[type_id] = list of 32-byte snapshots (one per sample)
        per_type: dict[int, list[bytes]] = defaultdict(list)
        # also store (frame_num, slot_idx, type_id, slot_bytes) for detailed view
        detail: list[tuple[int, int, int, bytes]] = []

        for sample in range(NUM_SAMPLES):
            msx.cont()
            time.sleep(0.4)
            raw = bytes(msx.read_memory(ENTITY_BASE, TABLE_SIZE))
            slots = parse_slots(raw)
            for slot_idx, (type_id, slot_bytes) in enumerate(slots):
                if type_id in TARGET_TYPES:
                    per_type[type_id].append(slot_bytes)
                    detail.append((sample, slot_idx, type_id, slot_bytes))
            if sample % 5 == 0:
                active = [(i, t) for i, (t, _) in enumerate(slots) if t in TARGET_TYPES]
                print(f"  sample {sample+1}/{NUM_SAMPLES}: "
                      f"active target slots = {active}")

        msx.remove_breakpoint(bp)
        print("Capture complete.")

    # ── Analysis ────────────────────────────────────────────────────────────────
    print("\n" + "="*72)
    print("ENTITY SLOT FIELD ANALYSIS")
    print("="*72)

    for type_id in sorted(per_type):
        samples = per_type[type_id]
        if len(samples) < 2:
            print(f"\nType {type_id}: only {len(samples)} sample(s), skip")
            continue

        print(f"\n── Type {type_id} ({len(samples)} samples) ──")

        # Find first occurrence: baseline values
        base = samples[0]
        print(f"  baseline: {hex_row(base)}")
        print()

        # For each offset 0x0C-0x1F, report:
        # - min/max across all samples
        # - whether it ever changes (dynamic vs static)
        print(f"  {'Off':>5}  {'base':>4}  {'min':>4}  {'max':>4}  {'range':>5}  status")
        print(f"  {'---':>5}  {'----':>4}  {'---':>4}  {'---':>4}  {'-----':>5}  ------")

        for off in range(0, 32):
            vals = [s[off] for s in samples]
            mn = min(vals)
            mx = max(vals)
            span = mx - mn
            uniq = len(set(vals))
            if uniq == 1:
                status = "STATIC"
            elif span <= 2:
                status = "jitter"
            elif vals == sorted(vals) or vals == sorted(vals, reverse=True):
                status = "MONOTONE"
            else:
                status = f"varies ({uniq} vals)"
            marker = " <" if off >= 0x0C and status != "STATIC" else ""
            print(f"  {off:#5x}   {base[off]:04X}   {mn:04X}   {mx:04X}  {span:>5}  {status}{marker}")

    # ── Per-type first-frame dump ────────────────────────────────────────────────
    print("\n" + "="*72)
    print("FIRST-FRAME FULL SLOT DUMPS (all 32 bytes)")
    print("="*72)
    seen_types = set()
    for sample, slot_idx, type_id, slot_bytes in detail:
        if type_id not in seen_types:
            seen_types.add(type_id)
            print(f"\nType {type_id} (slot {slot_idx}, sample {sample}):")
            for row_start in range(0, 32, 16):
                offs = " ".join(f"+{row_start+i:02X}" for i in range(16))
                vals = " ".join(f"  {slot_bytes[row_start+i]:02X}" for i in range(16))
                print(f"  {offs}")
                print(f"  {vals}")


if __name__ == "__main__":
    main()
