---
address: 0x716B
end: 0x71C4
kind: data
name: death_transition_table
confidence: confirmed
sprint: "0044"
tags: [collision, entity, death]
---

# death_transition_table

## Summary

90-byte byte array indexed by `entity_type & 0x7F`, mapping each entity type to
the **post-collision type** it becomes when it collides. `collision_response`
(0x453E) reads `transition_table[type]` for both colliding parties and writes the
result back to each slot's type byte (`slot+0x00`), so the next `entity_dispatch`
tick runs the new type's handler (explosion / despawn / damage). Covers types
0–89 (0x71C5 immediately follows with `random_x_pos`/prng code).

## Death classes

**Seven** distinct target values appear (this section previously said "five"
while listing seven rows). Their frequencies over types 0–89 are:

| Value | Count |
|-------|-------|
| 35 (explosion) | 53 |
| 40 (despawn) | 16 |
| 80 (base damage) | 16 |
| 60 (player death) | 2 |
| 0 / 19 / 39 | 1 each |

53 + 16 + 16 + 2 + 3 = 90, accounting for every entry.


| Value | = type | Meaning |
|-------|--------|---------|
| 0x00 | 0  | inactive (type 0 maps to itself — never collides) |
| 0x13 | 19 | → type 19 (fire-weapon-0 projectile becomes the type-19 converter) |
| 0x23 | 35 | the common enemy death target — **but see the conflict below** |
| 0x27 | 39 | → type 39 ground-column-marker (self-map for type 39) |
| 0x28 | 40 | **instant despawn** (handler = `entity_clear`) — shots, bullets, fragments |
| 0x3C | 60 | **player death explosion** (player type 1 → 60; type 60 self-maps) |
| 0x50 | 80 | **base damage handler** — wide ground structures route damage to type 80 |

## Notable entries

| Type(s) | → | Note |
|---------|---|------|
| 0 | 0 | inactive slot |
| 1 (player ship) | 60 | spawns the 11-frame death explosion |
| 2 (player shot) | 40 | shot vanishes on impact |
| 3 (fire weapon 0) | 19 | becomes the type-19 converter |
| 4–36 (most enemies) | 35 | standard explosion |
| 37, 38 (bullets/fragments) | 40 | despawn |
| 39 (col marker) | 39 | unchanged |
| 60 (death explosion) | 60 | already terminal |
| 70–89 (ground structures) | 80, except 72/80/82/83 → 40 | see below |

### Types 70–89 pinned down (2026-07-30)

"Scattered 40s" is exact rather than arbitrary — read straight from ROM:

```
70→80 71→80 72→40 73→80 74→80 75→80 76→80 77→80 78→80 79→80
80→40 81→80 82→40 83→40 84→80 85→80 86→80 87→80 88→80 89→80
```

The four exceptions are precisely the **non-structures** in that range, so the
rule is cleaner than it looks: anything that is actual ground structure routes
damage to type 80, while the orb/pickup entities simply vanish.

| Type | → | Why it despawns rather than taking damage |
|------|---|-------------------------------------------|
| 72 | 40 | base core / warp **orb** — collected, not destroyed ([[idol-warp-orbs]]) |
| 80 | 40 | the base-damage handler itself; terminal, so it self-terminates |
| 82 | 40 | **fire-powerup box**, a pickup (sprint 0061, screenshot-confirmed) |
| 83 | 40 | the fire upgrade the box drops |

## Type 35 is the enemy **death** entity, not a projectile (2026-07-30)

Reading 0x8446's first-frame path (type-byte bit 7 still clear) settles the
conflict recorded below in favour of this file's "explosion" reading:

```
8446  BIT 7,(IX+0); JP NZ,0x84C9     ; already running -> body
844D  LD HL,0xE12F; LD A,0x10; ADD A,(HL); LD (HL),A
8454  CALL C,0xBFAB                  ; inc_encounter_a
8457  LD A,(0xE142); CP 0x11; ...    ; index shot_rate_table (0x7761)
846B  LD HL,0xE131; ADD A,(HL); LD (HL),A; CALL C,0xBFC8
8473  LD A,(0xE141); CP 8; ...       ; A = 0x24 - 4*E141  (or 1 when >= 8)
8484  LD HL,0xE131; ADD A,(HL); LD (HL),A; CALL C,0xBFC8
848C  SUB A; LD (0xE142),A; LD (0xE141),A   ; consume both counters
8493  LD A,0x11; CALL play_sound_event      ; SFX event 17
8498  LD (IX+0),0xA3                        ; type 35, active bit set
```

Three things make "enemy projectile" untenable for this entity:

- It **feeds the ALC spawn accumulators** (0xE12F and 0xE131, with carry into
  `inc_encounter_a` / 0xBFC8). Adaptive difficulty is driven by how effectively
  the player destroys things — an enemy's own bullet appearing has no business
  advancing that schedule.
- It **consumes and zeroes 0xE141/0xE142**, the *player's* fire-event counters,
  and weights the contribution by them (`0x24 - 4 × E141`): the fewer shots it
  took, the bigger the nudge. That is kill accounting.
- It plays a one-shot SFX and only then marks itself active.

This is also what `CLAUDE.md` means by ALC family 1's "base path
`handler_type35` 0x8446". The misnomer therefore sits in
[[handler_type35_projectile]] / [[entity_jump_table]] / [[entity-sprite-mapping]],
which appear to have been written from the sprite-pool selection in the running
body without seeing this init.

**Still unread:** the running body at 0x84C9, so the on-screen form (animation
frames, lifetime, whether it drifts) is not yet characterised — only its role.

## Superseded: the conflict as originally raised

This entry calls 35 the "standard enemy explosion", and 53 of the 90 types map
to it on death, so it is certainly the common death target. But the KB describes
the handler it dispatches to in incompatible terms:

| Source | Says 0x8446 is |
|--------|----------------|
| this file | standard enemy **explosion** |
| [[handler_type35_projectile]] | enemy **projectile** |
| [[entity_jump_table]] row 35 | "enemy projectile — sprite chosen from 0xE141 counter (lead/circle/plane range); NOT base-eye (corrected sprint 0013)" |
| [[entity-sprite-mapping]] row 35 | pattern from 0xE141 across the full sprite pool |
| `CLAUDE.md` (subsystem I) | ALC "base path `handler_type35` 0x8446" |

Both readings are plausible on the evidence quoted: a death explosion and a
spawned projectile would each pick a sprite from a pool and run a short life.
Nothing in the KB shows the handler body, and no sprint appears to have watched
a slot *after* it was remapped to 35.

**Resolved above** by reading 0x8446's init path: the ALC bookkeeping and the
consumption of the player's fire counters make it the death entity. The section
is kept because the three files listed still carry the projectile label and
should be corrected at their own addresses.

## Live confirmation (sprint 0044)

Captured at `collision_response` over real shot-vs-enemy hits: IX type 44 → 35,
type 4 → 35; IY type 2 → 40 — each equals `ROM[0x716B + type]`. Full 90 bytes
read directly from ROM. `tools/sprint0044_verify.py`.

## See also

- `collision_response.md` — 0x453E, the sole reader (referenced at 0x4549/0x4557).
- `entity_jump_table.md` — the type → handler map the remapped type then selects.
