---
address: 0x8F9A
end: 0x8FA2
kind: data
name: scroll_speed_ramp_table
confidence: likely
sprint: "0063"
tags: [scroll, base-encounter, data-table, subsystem-d]
---

# scroll_speed_ramp_table

9-byte scroll-speed ramp (`0C 11 14 17 1A 1D 20 23 26`) used by the
base/boss **encounter scroll-mode controller** `sub_8f5e` (0x8F5E): as a
structure/boss is approached it ramps `E710` (current_scroll_speed) up
through these values (documented in [[main_game_loop]]; dispatch on `E150`
base_encounter_flags → 0x934D / 0x9028).

`confidence: likely` — reader + purpose documented in the confirmed
[[main_game_loop]] analysis, but the table itself has not been individually
live-toggled. Cheap upgrade in sprint 0067 (poke a value, watch E710 ramp).

## See also

[[main_game_loop]], `sub_8f5e` (0x8F5E), `E710` current_scroll_speed.
