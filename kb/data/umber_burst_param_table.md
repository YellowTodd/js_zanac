---
address: 0x79b7
end: 0x79bd
kind: data
name: umber_burst_param_table
confidence: confirmed
sprint: "0049"
tags: [entity, enemy, umber]
---

# umber_burst_param_table

7 bytes consumed by [[handler_type7_umber]] (0x791d) when a type-7 umber stops
at the top of the screen and bursts into **7 type-38 fragments**. The burst loop
(0x798e–0x79ac, `B=7`) spawns one fragment per byte and stores the byte into the
child's +0x1a field (per-fragment spread parameter).

| # | byte |
|---|------|
| 0 | 0x04 |
| 1 | 0x05 |
| 2 | 0x02 |
| 3 | 0x07 |
| 4 | 0x03 |
| 5 | 0x06 |
| 6 | 0x01 |

## Source note

Labelled `DB` block `umber_burst_param_table:` in source (sprint 0053; was
mis-decoded as instructions). No `DD` absorption here — the table's last bytes
decoded as `LD B,0x01`, so the type-8 umber entry 0x79be was already correct.
