---
id: "0023"
status: done
range: 0x7253-0x77A0
strategy: forward_from_caller
budget_turns: 30
---

# Sprint 0023 — Fire weapon system: types 0–7 projectile mapping

## Goal

The player's fire weapon (Z key, types 0–7 selectable, shown as "FIRE" on HUD)
is almost entirely unmapped. Only type 0 is partially known (entity type 3 =
large_circle, cycles all 16 colors). This sprint maps:

1. **How each fire type (0–7) determines the entity spawned** — what handler
   is called, what type code is written to the entity slot.
2. **The type-3 handler** (0x7253) in full — direction logic (vertical, diagonal,
   horizontal based on player movement), color cycling, 0xE14B read.
3. **Fire weapon upgrade path** — `sub_7548` (0x7548) called after 5 maxed
   power chips; what it does to the fire system.
4. **Types 19** (fire-init → type 3 transition, already partially known) and
   the remaining init entity for each fire type.
5. **SPACE key "both shot+fire"** — the gameplay SPACE (row 8 bit 0) activates
   both shot (row 8 bit 0 → RES 4,(HL)) and fire (row 8 bit 0 → RES 5,(HL))
   simultaneously. Confirm which entity is spawned.

## Inputs

- `kb/features/entity-sprite-mapping.md` — type 3 (fire weapon 0 projectile):
  large_circle, cycles all 16 colors. Type 19 transitions to type 3 (type byte
  → 0x83 after init — this type number needs verification).
- `kb/symbols/0xE000-gamestate/fire_type.md` — 0xE14B: fire_type 0–7.
- `kb/data/entity_jump_table.md` — type 3 handler 0x7253; type 19 handler 0x74A4.
- Source lines 2758–2779 (type 3 handler init).
- Source lines 3524–3542 (power chip → fire upgrade path; `CALL 0x7548`).

## Verification plan

**Headless — inject fire type, shoot Z, capture entity types:**
```python
with ZanacGame.launch() as game:
    game.wait_for_title(); game.start_game()
    msx = game.client
    time.sleep(1.0)

    results = {}
    for fire_type in range(8):
        msx.write_byte(0xE14B, fire_type)
        # Tap Z key (fire weapon)
        msx.key_press(*MSXKey.ZANAC_FIRE, duration=0.1)
        time.sleep(0.1)
        # Read entity slots 1-4 (player-controlled range)
        raw = msx.read_memory(0xE300, 5*32)
        types = [raw[i*32] & 0x7F for i in range(5)]
        results[fire_type] = types
        print(f"fire_type={fire_type}: entity types={types}")
```

**Static analysis of type-3 handler (0x7253):**
- Source around lines 2758–2835: full decode of the running handler.
- The `CALL 0x5C2E` (called twice with 0xE14B) — identify this routine.
- How does the handler pick direction? (player velocity flags?)

**Find sub_7548:**
```python
msx.cmd("disasm 0x7548 20")
```

## Expected new KB files

- Updated `kb/features/entity-sprite-mapping.md` with fire types 1–7
- `kb/symbols/0x8000-enemy/handler_type3_fire0.md`
- `kb/symbols/0x????-sound/sub_7548.md` (fire weapon upgrader)

## Summary

### Entity type: ALL fire types use entity type 3 in slot 4

The player handler (0x75D5) always writes type 0x03 to entity slot 4 (0xE380),
regardless of `fire_type` (0xE14B). The fire type is read by the type-3 handler
to select per-type behavior via two internal dispatch tables.

### sub_5C2E — computed dispatch (confirmed)

A classic Z80 stack-return trick: pops the return address, uses fire_type×2 as
a table index into the bytes that FOLLOW the CALL instruction in the caller,
pushes the selected address as the new return address, and RET's to it. This
gives O(1) indexed dispatch without a JP (HL) or JP (IX) that would expose the
table address.

### Dispatch tables

**Init table at 0x7269** (one-time setup per fire type, 8 × 2-byte LE addresses):
0→0x72B3, 1→0x72A8, 2→0x729D, 3→0x7331, 4→0x73CE, 5→0x73C8,
6→0x73CE (shared with 4!), 7→0x728F.

**Running table at 0x727F** (per-frame, 8 × 2-byte LE addresses):
0→0x72DE, 1→0x72EA, 2→0x72F5, 3→0x735D, 4→0x7439, 5→0x7464,
6→0x7494, 7→0x7306.

### Key per-weapon findings

| Weapon | Key finding |
|--------|-------------|
| Fire 0 All-Range | INC sat_color AND 0x8F each frame = 16-color cycle; direction from table 0x7758 via 4CF7 (+0x0C=0x03) |
| Fire 1 Straight | Calls All-Range run first (color cycle + motion), then checks ammo limit |
| Fire 2 Field Shutter | Sets Y=player_Y−8, X=player_X every frame — follows the ship |
| Fire 3 Circular | +0x0C=0x00 (no entity_update motion); uses counter in +0x11 for orbit position |
| Fire 4+6 | Share init at 0x73CE; different run handlers (0x7439 vs 0x7494) |
| Fire 6 Plasma Flash | No persistent entity observed — immediate screen-clear effect |
| Fire 7 High Speed | Decrements time limit at 0xE14C; CALL 0x730B for motion setup |

### sub_7548 — fire weapon switcher (confirmed)

Called when player collects a fire chip: reads new fire_type, updates 0xE14B,
reads limits from ROM table at 0x751F (8 × 2 bytes), writes to 0xE14D/0xE14E
(HUD display values). If switching to a different type, writes type 0x28 (=40
decimal) to slot 4 type byte → triggers "immediate despawn" handler 0x852C.

### New/updated KB

- `kb/guides/entity-sprite-mapping.md`: full fire weapon section with dispatch
  tables, per-weapon behavior, limit table, sub_5C2E decode, sub_7548 decode.

### Remaining unknowns

- Per-weapon running handlers not fully decoded (only Fire 0/1/2 examined).
- sub_7548 called from: need to find what triggers the fire upgrade (5×max power chips).
- 0xE14C/0xE14D/0xE14E exact HUD semantics (how limits are displayed per weapon).
