---
address: 0x4D45
end: 0x4D64
kind: data
name: dir_remap_table
confidence: confirmed
sprint: "0063"
tags: [velocity, direction, data-table]
---

# dir_remap_table

32-byte direction remap table used by [[set_velocity_from_dir]] (0x4CF7):
after [[dir_angle_thresholds]] classifies the angle octant, this table maps
(octant, quadrant) to the final 16-direction index that selects a signed
X/Y unit vector from [[vel_dir_table]] (0x4D65). Disassembled + labelled in
sprint 0048; this entry (0063) adds the KB extent for the coverage audit.

## See also

[[set_velocity_from_dir]], [[dir_angle_thresholds]], [[vel_dir_table]].
