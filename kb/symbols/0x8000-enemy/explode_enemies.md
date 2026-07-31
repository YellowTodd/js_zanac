---
address: 0x8A26
kind: routine
name: explode_enemies
confidence: confirmed
calls:   [0x0047, 0x5BEC]
called_by: [0x914F]
sprint: "0067"
tags: [enemy, video, base]
---

# explode_enemies

## Summary
Flash screen by blanking display, then replace all living enemy sprites with explosion type 0x23.

## Analysis
Source lines 2860–2882. Calls WRTVDP (0x0047) with BC=0x0F07 (R7=0x0F border colour?), waits B=5 frames (wait_frames 0x5BEC). Then iterates 0x15 enemy slots at 0xE3A0 (stride 0x20=32 bytes/slot): any slot whose type byte & 0x7F is in [0x01,0x45] and ≠ 0x28 is replaced with type 0x23 (explosion). JP WRTVDP BC=0x0107 (R7=0x01 restore colour) as tail-call.

## Live confirmation (sprint 0067, `tools/verify_explode_enemies.py`)

Called from the **base-clear routine at 0x914F** (`LAB_ram_914e`, part of the
0x9165 clear/award path — see [[base_clear_award_index_table]]). In a round-1
base fight, breaking at 0x8A26 caught **2 entries** on the base clear; a slot
snapshot at the second entry showed living enemies (types 0xA5, 0x8D, 0x27)
already **converted to 0xA3 = active(0x80) | explosion 0x23** — exactly the
type-0x23 replacement this routine performs. Confirmed it screen-flashes and
wipes all live enemies to explosions on a base clear (also the yellow "kill-all"
warp-orb effect, [[idol-warp-orbs]]). Upgraded `hypothesis` → `confirmed`.
