---
address: 0x976C
end: 0x977C
kind: data
name: cmd11_index_table
confidence: likely
sprint: "0063"
tags: [scroll, map-script, data-table]
---

# cmd11_index_table

17-byte index table (`00 02 02 00 03 03 02 03 03 03 04 01 00 00 00 07 03`)
used by map-script **command 0xB** (handler 0x9742, [[level_script_format]]):
the special stream-slot config copies 4 operand bytes to 0xE155–0xE158,
clears 0xE154, then indexes this table by `0xE157 & 0x1F` → 0xE153 before
initialising slot 0 via `init_stream_slot` (0x95C0). Labelled in sprint 0056;
this entry (0063) adds the KB extent for the coverage audit. What the indexed
value selects (0xE153 consumer) is a sprint 0062 item.

## See also

[[level_script_format]] (cmd 0xB), `init_stream_slot` (0x95C0).
