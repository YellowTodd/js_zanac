---
address: 0x7748
end: 0x7757
kind: data
name: dir8_delta_table
confidence: likely
sprint: "0065"
tags: [player, direction, data-table, unreferenced]
---

# dir8_delta_table

8 signed word deltas (`+0x0001, +0x0019, +0x0018, +0x0017, -0x0001, -0x0019,
-0x0018, -0x0017`) — the classic 8-direction offsets for a 0x18(24)-wide
grid/name-table walk. **Unreferenced**: no reader was found when the
surrounding player-ship code was decoded (sprint 0048, noted in the asm label
comment). Likely a leftover from a map/tile neighbourhood helper that was
dropped; the ±0x18 stride matches a 24-column playfield.

`confidence: likely` on the "dead data" verdict — a computed-pointer reader
can't be fully excluded statically. **Sprint 0065 live evidence
(`tools/verify_orphan_data.py`):** a read-watchpoint over the full range
0x7748–0x7757 stayed at **zero hits** through a ~45 s active play session
(continuous fire, weaving, many ground-structure destructions). Consistent with
dead data; kept `likely` because one session cannot exercise every code path
(round-specific handlers, base fights) — but no reader surfaced under active play.

Sprint 0065 line-update: `sprint: "0063"` → this note added under 0065.

## See also

[[xvel_table]] (follows at 0x7758), [[read_player_input]].
