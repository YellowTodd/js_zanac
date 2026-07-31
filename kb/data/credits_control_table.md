---
address: 0x4775
end: 0x4826
kind: data
name: credits_control_table
confidence: confirmed
sprint: "0063"
tags: [credits, ending, data-table, subsystem-l]
---

# credits_control_table

## Summary

Entry control table for the ending credits pages, walked by
[[credits_display]]'s page loop (`LAB_46E0`, `HL` starts at **0x4775**). Each
entry selects and centre-aligns a length-prefixed string from the **string
table at 0x47AA** (which occupies the tail of this run; strings decoded:
`GAME DESIGN`, `PROGRAM`, `GRAPHICS`, `SOUND`, `DIRECTOR`, `JANUS`, `JEMINI`,
`COMPILE`, `WAO`, `MOO`, `MIYAMOTO`, `YORIKI`, `THANKS`, `PAL`, `MUSIC`,
`LUNARIAN`). A `0xFF` terminator ends each page's entry list; the following
byte selects the next page. The logo tile rows continue at 0x4827
([[logo_tile_rows]], end 0x4897).

Decoded in sprint 0046 (subsystem L slice); credits rendering live-confirmed
by screenshot. This entry (0063) only gives the region its own KB extent so
the byte-coverage audit joins it — content documentation lives in
[[credits_display]].

## See also

[[credits_display]], [[init_credits_stream]], [[logo_tile_rows]].
