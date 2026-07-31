---
address: 0x8446
kind: routine
name: handler_type35_projectile
confidence: likely
inputs:  { IX: "entity slot" }
outputs: {}
clobbers: [AF, HL]
calls:   [0xBFAB]
called_by: [0x445F]
tags: [entity, base, animation]
sprint: "0012"
---

# handler_type35_projectile

> **Name under review (2026-07-30) — this is very likely the enemy *death*
> entity, not a projectile.** The first-frame path (0x844D–0x8498) feeds the ALC
> spawn accumulators 0xE12F/0xE131 (carrying into `inc_encounter_a` / 0xBFC8),
> then consumes and zeroes the **player's** fire-event counters 0xE141/0xE142,
> weighting its contribution by them (`0x24 − 4 × E141` — the fewer shots the
> kill took, the bigger the nudge), plays SFX event 17, and only then sets its
> own active bit. That is kill accounting, not a bullet being fired.
>
> Corroborating: [[death_transition_table]] maps **53 of 90** entity types to 35
> on collision, and `CLAUDE.md` names this routine as ALC family 1's "base
> path". Full analysis in [[death_transition_table]].
>
> **Update — the rest of the routine now read, and it confirms "explosion".**
>
> ```
> 8498  LD (IX+0),0xA3                ; type 35, active
> 849C  CALL add_score_for_subtype    ; 0x4A6A, indexed by +0x18 (the pre-hit type)
> 849F  SET 2,(IX+0x0C)               ; animate
> 84A3  (IX+0D)=1  (IX+0E)=4          ; tick, 4 frames per step
> 84AB  (IX+0F)=1  (IX+10)=6          ; start at frame 1, six frames
> 84B3  LD DE,0x84D1 -> (IX+11/12)    ; animation table
> 84BC  LD HL,0xE124; DEC (HL); JR NZ ; every 16th kill:
> 84C2    (HL)=0x10; (0xE125)=1       ;   raise a flag
> 84C9  LD A,(IX+0F); AND A
> 84CD  JP NZ,entity_update           ; still animating
> 84D0  JP entity_clear               ; frame wrapped to 0 -> gone
> ```
>
> It awards score through [[add_score_for_subtype]] using the type stashed by
> [[collision_response]], animates six frames, and deletes itself. That is a
> death explosion; nothing here fires or travels.
>
> **Animation table at 0x84D1 is data mis-decoded as code.** It holds six
> `(sat_name, sat_colour)` pairs — `D0 48 | 1C 8A | 20 8E | 24 8F | 20 8D |
> 1C 89` — i.e. patterns lead → med_circle → **lg_circle** → med_circle → lead,
> the classic expand-and-contract burst. In `zanac.asm` it is swallowed by the
> `JP 0x48D0` at 0x84D0 and then shown as `INC E` / `ADC A,D` / … from 0x84D3,
> so `coverage_audit` counts those bytes as code. Frame 0's entry is never
> displayed: the counter starts at 1 and reaching 0 despawns the entity.
>
> Renaming to something like `handler_type35_death_explosion` is left for a
> proper `rename_symbol` pass.

## Summary

Entity handler for type 35: a multi-pattern projectile/enemy. Picks one of
several bullet or structure sprite patterns based on `(0xE141)` (a game-state
counter adjacent to `spawn_event_ctr`). Live capture confirms patterns
7 (lead), 8 (medium_circle), 9 (large_circle), and 16 (plane) are all possible
for different instances of type 35.

**Correction from sprint 0012:** previously mis-labelled `handler_type35_base_eye`.
Live data disproves the base-eye hypothesis — the handler spawns visible
projectiles/enemies across the screen, not a base-eye animation.

## Analysis

```
8446  BIT 7,(IX+0)
844A  JP NZ, 0x84C9      ; initialized: running code
844D  LD HL, 0xE12F
8450  LD A, 0x10
8452  ADD A, (HL)         ; 0xE12F += 16 each frame (animation frame sub-counter)
8453  LD (HL), A
8454  CALL C, 0xBFAB      ; on overflow: call base_encounter_ctrl increment
8457  LD A, (0xE142)      ; read animation phase counter
845A  CP 0x11             ; compare to 17
845C  JR C, 0x8462        ; < 17 → first phase
845E  LD A, 0x01
8460  JR 0x8473           ; second phase
```

### Connection to base health display

- 0xE12F: fine-grained frame accumulator (adds 16/frame, wraps ~16 frames)
- 0xE142: animation phase counter (compared to 17 for two-phase eye animation)
- On overflow of 0xE12F: calls `base_encounter_ctrl` 0xBFAB which increments
  0xE12E and rewrites the VRAM display at 0x3839/0x3859
- 0xE130: the base health counter read by `handler_type11_base_spawner` and
  `base_encounter_ctrl` to determine projectile positions and HUD display
