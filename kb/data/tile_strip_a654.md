---
address: 0xA654
end: 0xA65B
kind: data
name: tile_strip_a654
confidence: likely
sprint: "0066"
tags: [scroll, tile, level-map, data-block, d-scroll]
---

# tile_strip_a654 (0xA654–0xA65B, 8 B)

An 8-byte tile strip — `6F 70 71 72 1D 72 7B 7C` — wedged between the end of
[[tile_tables]] (…0xA653) and the first map script (0xA65C). It is a direct
continuation of `tile_tables`' fixed base-layer tile columns: the preceding
bytes run the same tile-ID alphabet (`…7C 6F 70 72 1D 72 7A 7B 7C 67 6F 71 1D
7A 7C 67`), so this is one more fixed vertical tile column of the same kind,
addressed by a fixed offset from the `tile_tables` consumer (`sub_9888` /
`sub_4236`) rather than by a map-script pointer (no script column pointer
targets 0xA654).

`confidence: likely` — identified as tile-column data by content and adjacency;
its exact fixed-offset reader is shared with [[tile_tables]].

## See also

[[tile_tables]], [[tile_column_data_region1]], [[level-data-block-map]].
