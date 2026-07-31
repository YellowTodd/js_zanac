---
address: 0x4D42
end: 0x4D44
kind: data
name: dir_angle_thresholds
confidence: confirmed
sprint: "0063"
tags: [velocity, direction, data-table]
---

# dir_angle_thresholds

Three octant angle cut-points (`0x32, 0x6A, 0xAB`) used by
[[set_velocity_from_dir]] (0x4CF7) to classify an angle byte into an octant
before remapping through [[dir_remap_table]] (0x4D45). Disassembled + labelled
in sprint 0048 (the whole 0x4CF7–0x4DA4 block was a mis-typed `DB` region);
this entry (0063) adds the KB extent for the coverage audit.

## See also

[[set_velocity_from_dir]], [[dir_remap_table]], [[vel_dir_table]].
