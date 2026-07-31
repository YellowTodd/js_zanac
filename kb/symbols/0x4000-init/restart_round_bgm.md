---
address: 0x4163
end: 0x4176
kind: routine
name: restart_round_bgm
confidence: confirmed
inputs: {}
outputs: {}
clobbers: [AF]
calls:   [0x5189]
called_by: [0x413a, 0x91ec, 0x9388]
tags: [sound, gamestate, base, level-transition]
sprint: "port"
---

# restart_round_bgm

The **"put the theme back on" helper**. Thirteen bytes, but the only thing that
ever restarts the round's background music after something silenced it:

```
4163  LD A,(0xe102) / BIT 7,A / RET NZ    ; demo mode -> stay silent
4169  LD A,(0xe701) / AND 0x07            ; round & 7
416e  LD A,0x01
4170  JP NZ,0x5189                        ; ordinary round -> event 1
4173  INC A
4174  JP 0x5189                           ; round ≡ 0 (mod 8) -> event 2
```

Note it plays event **1** (the main theme itself), not event 7 — the round-start
jingle the main loop uses at 0x405A, which only *chains* to 1 when it finishes.
See [[sound_events]].

## Callers — all three are "the music was stopped, hand it back"

| from | situation |
|------|-----------|
| 0x413A | [[level_complete_handler]], after a round transition reloads tiles |
| **0x91EC** | [[base_tick]]'s victory ceremony, for any base scenario < 0x0F (`SUB 0x0F / JP C,0x4163`) |
| **0x9388** | [[base_tick]]'s closing sweep, when a scenario-bit-5 base finishes retreating after its clock ran out |

The two base callers matter because the ceremony's fanfare path ends in
`stop_all_sound` (0x9180): after the bonus tune there is **nothing playing**,
and 0x4163 is what refills the PSG. A port that ends the ceremony without it
leaves the game permanently silent from the first boss onward — the symptom
that found this entry (2026-07-30).

## Related

[[base_tick]], [[level_complete_handler]], [[play_sound_event]] (0x5189),
[[fade_music_out]] (0x5211, the counterpart that ramps the theme *down* when a
base opens).
