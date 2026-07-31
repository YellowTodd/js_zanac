---
address: 0xE103
kind: data
name: score_lo
confidence: confirmed
sprint: "0067"
tags: [game-state, score]
---

# score_lo

## Summary
Score BCD byte 0 (digits 1-2, e.g. 0x60 = '60'). Base of the 3-byte BCD score
written by [[add_score]] (0x4A74: `LD DE,0xE103` … `DAA`); **live-confirmed
sprint 0065** — awarding a structure gave the exact BCD delta from
[[score_award_table]] here. Upgraded `likely` → `confirmed`.
