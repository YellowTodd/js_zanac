---
address: 0xE104
kind: data
name: score_mid
confidence: confirmed
sprint: "0067"
tags: [game-state, score]
---

# score_mid

## Summary
Score BCD byte 1 (digits 3-4, e.g. 0x34 = '34'). Written by [[add_score]] (the
`INC DE` + `ADC`/`DAA` carry chain from [[score_lo]]); **live-confirmed sprint
0065** via structure score awards. Upgraded `likely` → `confirmed`.
