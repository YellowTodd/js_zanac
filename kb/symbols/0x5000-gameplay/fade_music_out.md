---
address: 0x5211
end: 0x5235
kind: routine
name: fade_music_out
confidence: confirmed
inputs: {}
outputs: {}
clobbers: [AF, B, DE, IX]
calls:   []
called_by: [0x8fb1, 0x9342]
tags: [sound, psg, base]
sprint: "port"
---

# fade_music_out

**Not a stop.** It walks the **three music voice slots** (0xE20C, stride 0x1B —
see [[psg_voice_slots]]) and arms each one's volume envelope so the tune ramps
down while continuing to play:

```
5211  DI / PUSH IX
5214  LD IX,0xe20c / LD DE,0x001b / LD B,0x03
521d  SET 5,(IX+0x08)        ; VOL_ENV active
5221  LD (IX+0x16),0x08      ; envelope target amplitude
5225  LD (IX+0x14),0x10      ; envelope rate
5229  LD (IX+0x15),0x00      ; accumulator
522d  ADD IX,DE / DEC B / JR NZ
5232  POP IX / EI / RET
```

The SFX voices (slots 3 and 4) are untouched, so explosions keep their full
volume while the theme recedes — which is the point.

## Callers

| from | situation |
|------|-----------|
| 0x8FB1 | [[base_tick]]: a base with scenario bit 5 **opens**, so the theme ducks under the encounter |
| 0x9342 | [[base_tick]]: the same scenario's clock runs out |

Both are gated on `0xE102` bit 7 being clear (demo mode stays silent). The
counterpart that brings the music back is [[restart_round_bgm]] (0x4163).

Distinct from [[stop_all_sound]] (0x516C), which silences every voice and the
mixer outright; using that here cuts the theme dead instead of fading it.

## Related

[[base_tick]], [[restart_round_bgm]], [[stop_all_sound]], [[sound_events]]
