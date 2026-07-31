---
id: "0026"
status: done
range: 0x7F84-0x7F98
strategy: forward_from_caller
budget_turns: 8
---

# Sprint 0026 — Player-tracking entities (types 31 and 33)

## Goal

Types 31 and 33 share handler 0x7F84 and are labelled "player-tracking entity
— reads 0xE301 (player Y)" in the jump table. Sprint 0021 decoded
`entity_update` bit3 as the Y-homing system (+0x13=target_Y, +0x15=Y_accel,
+0x17=iterations) and partially decoded code around source lines 3262–3316
that reads 0xE301 and drives the entity toward the player's Y coordinate.

This sprint finishes that decode: confirm what init values are set, how the
entity tracks the player, and whether it also fires projectiles.

## Inputs

- `kb/data/entity_table.md` — bit3 homing fields (+0x13, +0x15, +0x17)
- `kb/data/entity_jump_table.md` — type 31 handler 0x7F84; type 33 same
- Sprint 0021 partial decode: lines ~3262–3316 show `LD A,(0xE301)`,
  `LD (IX+0x13),A`, accumulation in +0x0D/+0x0E, and a DJNZ loop
- `entity_update` bit3 at 0x4942 (decoded sprint 0021)

## Verification plan

**Static:** Read ROM at 0x7F84–0x7FFF via `msx.read_memory()` and decode
the init/running split. Check bit3 of +0x0C; read +0x13, +0x15, +0x17 init
values.

**Live:** Inject type 31 (0x1F | 0x80 = 0x9F) into a free entity slot,
position it away from the player, and observe over 30 dispatch breaks:
- Does Y converge toward player Y?
- Does the entity fire a projectile at any point?
- What sprite pattern does it use?

```python
with ZanacGame.launch() as game:
    game.wait_for_title(); game.start_game()
    msx = game.client
    time.sleep(1.5)

    # Write type-31 (pre-initialized, bit7 set) directly into slot 5
    SLOT5 = 0xE3A0
    msx.write_byte(SLOT5 + 0x00, 0x9F)  # type=31, active
    msx.write_byte(SLOT5 + 0x01, 0x20)  # Y = 32 (top of screen)
    msx.write_byte(SLOT5 + 0x02, 0x60)  # X = 96
    msx.write_byte(SLOT5 + 0x03, 0x1C)  # sat_name = lead
    msx.write_byte(SLOT5 + 0x04, 0x8F)  # color

    # Observe 30 frames, track Y convergence
    for _ in range(10):
        msx.cont(); time.sleep(0.15)
        py = msx.read_byte(0xE301)
        s  = bytes(msx.read_memory(SLOT5, 32))
        print(f"playerY={py}  entityY={s[1]}  +09={s[9]:02X}  +13={s[0x13]:02X}  +0C={s[0xC]:02X}")
```

## Focus questions

1. What is +0x0C for type 31? (Hypothesis: bit3 set → uses entity_update Y-homing)
2. What values are in +0x13 (target_Y), +0x15 (accel), +0x17 (iterations)?
3. Does type 31 fire projectiles, and if so which entity type?
4. What distinguishes type 31 from type 33?

## Expected output

- New `kb/symbols/0x8000-enemy/handler_type31_tracker.md`
- Updated `kb/data/entity_jump_table.md` (confidence: hypothesis → confirmed)

## Summary

### Method
Two passes: (1) ROM read of 0x7F73–0x8080 and supporting tables; (2) live
injection of type-31 (pre-activated) into slot 5, 30 dispatch-break observations.

### Finding 1 — Two distinct behaviours at two entry points

| Entry | Types | Behaviour |
|-------|-------|-----------|
| 0x7F84 | 31, 33 | **Stealth tracker** — no init, pure running code; closes on player Y, flanks via X |
| 0x7F99 | 34, 65, 66 | **Stealth shooter** — standard init check; fires projectile bursts on timer |

Both share the init body at 0x7FA0 for types 34/65/66 (types 31/33 are
pre-initialized at spawn; their handler has no init phase).

### Finding 2 — Type 31/33: stealth tracker (confirmed)

**Running path (0x7F84 → 0x7F73):**
```
7F84  LD A,(0xE301)      ; player Y
7F87  CP (IX+0x01)       ; vs entity Y
7F8A  BIT 6,(IX+0x05)    ; "above" flag
7F91  JR NC, 0x7F73      ; player below: Y-motion toward player
7F93  LD (IX+0x0C),0x02  ; player above/level: switch to X-motion
7F97  JR 0x7F73

7F73  LD A,(IX+0x04); XOR 0x06; LD (IX+0x04),A   ; color flicker (0x88↔0x8E)
7F7B  CALL 0x4898         ; entity_update (applies velocity + SAT push)
7F7E  JP 0x44BA           ; entity_post (collision)
```

- **Sprite:** pattern 51 (stealth, sat=0xCC), color 0x88 (dark blue-grey)
  flickering with 0x8E (light green) every frame via XOR 0x06
- **Motion:** vy=+2 downward via entity_update bit0 (Y-motion). When entity
  Y catches up to player Y, +0x0C switches to 0x02 (X-motion) to flank.
- **Does NOT fire projectiles.** No spawn code on any running path.
- **entity_update bit3 Y-homing NOT used.** +0x13/+0x15/+0x17=0 throughout.
  Tracking is done manually: compare player Y, keep vy fixed at +2.

**Corrected sprint 0021 note:** "source lines 3262–3316 shows player-tracker"
was a misidentification — those lines are the fire-weapon Field Shutter X-tracker
(fire type 2 running code at 0x72F5–0x7330), not the type-31 handler.

### Finding 3 — Type 34/65/66: stealth shooter

Init (0x7FA0, entered when bit7=0):
- `CALL 0x71DA` → spawn col-marker; write sat_name=0xD0 (stealth_compl) into it
- `R AND 0x06` → random spawn column from table 0x807C (4 options)
- `CALL 0x4CF7` → set initial velocity from table param
- Set sat_name=0xCC (stealth), color=0x88, counters
- Type34 override (0x800E): `SET 0,(IX+0x05)` → enables SFX on firing
- Type65 override (0x7FE8): different color/counter values; 6th extra override at 0x7FFC (byte-overlapping trick with JR NZ 0x7FFE)

Running (0x8012):
- Decrement +0x1D countdown; reload from +0x0D when zero
- Compare player Y vs entity Y → pick spawn table 0x8084 or 0x8087
- Loop `B = IX+0x1E` times: allocate entity slots, init projectiles at offsets
  from entity X/Y per table bytes
- If bit0 of +0x05: play SFX #21 (type-34 fires audibly; 31/33 are silent)
- Call entity_update + 0x71F6 + JP 0x82A7

### Finding 4 — Spawn table 0x807C decoded

| R & 0x06 | X position | Velocity param |
|----------|-----------|----------------|
| 0 | 32 (left) | 0x02 |
| 2 | 208 (right) | 0x06 |
| 4 | 80 (center-left) | 0x04 |
| 6 | 160 (center-right) | 0x04 |

### Finding 5 — sub_730B (0x730B): fire weapon life-timer

```
730B  LD HL, 0xE14C; DEC (HL); RET NZ   ; decrement primary limit
7310  LD (HL), 0x3C; CALL 0x7594        ; reload to 60
7315  LD HL, 0xE14D; DEC (HL)           ; decrement secondary limit
731A  CP 0xFF; RET NZ                   ; not expired
731D  POP HL; JP 0x7544                 ; fire weapon expired → despawn
```

Used by fire types 5 (Rewinder) and 7 (High Speed) via CALL 0x730B in their
per-frame running code. Confirmed as the "time-limited" ammo counter mechanism.

### Focus questions answered

| Question | Answer |
|----------|--------|
| +0x0C for type 31? | 0x01 (Y-motion via entity_update bit0); switches to 0x02 (X-motion) when Y aligned |
| +0x13/+0x15/+0x17 values? | All 0; entity_update bit3 NOT used |
| Does type 31 fire? | No. Running path has no projectile spawn code. |
| Type 31 vs 33? | Identical handler 0x7F84; differ only by entity_jump_table index (no behavioral difference found) |
| Type 34? | Stationary stealth shooter with timer; fires IX+0x1E projectiles per burst |

### New KB artefacts

- `kb/symbols/0x8000-enemy/handler_type31_stealth_tracker.md` — full decode
- `kb/data/entity_jump_table.md` — types 31/33 → confirmed; 34/65/66 → likely
- `kb/guides/entity-sprite-mapping.md` — stealth tracker/shooter rows added
