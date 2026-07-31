---
id: "0017"
status: done
range: ~
strategy: live_debug
budget_turns: 40
---

# Sprint 0017 — Autonomous openMSX control

## Goal

Map how to programmatically drive openMSX with the Zanac ROM: launch headless,
detect every game phase, control the ship, and detect in-game events — without
any human input.

## Inputs

- `kb/features/openmsx-control.md` — wire protocol reference
- `tools/zanackb/openmsx.py` — existing thin client
- `tools/sprint0010_debug.py`, `tools/sprint0016_debug.py` — working patterns

## Verification plan

Automated Python test: launch → title → start → move + shoot → detect kills/
collision → game over → skip to title → start again. All states confirmed live.

## Summary

### 1. Launch and power-on

```python
client, proc = OpenMsxClient.connect_subprocess(rom="source/zanac.rom")
client.power_on()   # CPU starts running immediately (no cont() needed)
```

**Critical:** Set breakpoints BEFORE `power_on()` to avoid race conditions.
After `power_on()` the CPU is already running (`debug breaked` = 0).

**`debug running` does NOT exist** — use `debug breaked` (returns "1" when
paused, "0" when running).

**BIOS takes ~2s** before calling the cart INIT at 0x4010. A BP there is the
reliable "cart has started" signal.

### 2. Screen-state detection (primary method)

Read the VRAM name table at **0x3800** (not 0x1800) — 768 bytes = 24×32 tiles.
Tile codes match ASCII for text characters. Check for:

| String in VRAM | Meaning |
|---|---|
| `"COMPILE"` | Title screen (company logo, waiting for SPACE) |
| `"PAUSE"` | Game paused via STOP key |
| `"GAME OVER"` | Game-over screen |
| `"ZANAC"` | Gameplay active (lives displayed as ZANAC lettering) |

Implementation: `OpenMsxClient.read_name_table()` → `detect_screen(text)`.

Title screen appears **~1 second** after `power_on()` (no `cont()` needed).

### 3. Keyboard injection

`keymatrixdown row mask` / `keymatrixup row mask` write directly to the virtual
MSX keyboard matrix. The game reads this via BIOS `snsmat` (0x0141). Row/bit
confirmed from source analysis:

| Action | Row | Mask | Confirmed from |
|---|---|---|---|
| SPACE (title start, also gameplay) | 7 | 0x04 | `check_start_key` 0x43D2 reads row 7 bit 2 |
| SPACE (gameplay — both shot+fire) | 8 | 0x01 | movement handler row 8 bit 0 |
| UP ↑ | 8 | 0x20 | row 8 bit 5 |
| DOWN ↓ | 8 | 0x40 | row 8 bit 6 |
| LEFT ← | 8 | 0x10 | row 8 bit 4 |
| RIGHT → | 8 | 0x80 | row 8 bit 7 |
| SHIFT (shot only) | 6 | 0x01 | row 6 bit 0 |
| Z (fire weapon only) | 5 | 0x80 | row 5 bit 7 |
| STOP (pause indicator) | 7 | 0x10 | row 7 bit 4 |

**Important:** inject SPACE on BOTH row 7 bit 2 AND row 8 bit 0 for the title
screen — the game checks row 7 bit 2 in `check_start_key` (0x43D2) and row 8
bit 0 in the movement handler.

`keymatrixdown` holds the key low until `keymatrixup`. For a reliable key press:
hold ~100ms, release, wait ~300ms, then check screen state.

### 4. In-game event detection

**Ship collision** — write-watchpoint on `lives` (0xE10A), conditional on
value decreasing:
```tcl
debug set_watchpoint write_mem 0xe10a
  {[debug read memory 0xe10a] < $::prev_lives}
  {set ::prev_lives [debug read memory 0xe10a]; set ::collision 1}
```

**Enemy kill / score event** — write-watchpoint on `score_lo` (0xE103):
```tcl
debug set_watchpoint write_mem 0xe103 {} {incr ::kill_count}
```
Note: also fires on non-kill score sources (pickups, bonuses). Treat as
"score event" not strictly "enemy kill".

### 5. Key negative findings

- `E102` is NOT the game-phase discriminator — it is 0x00 in both title and
  gameplay states. Screen text is the only reliable phase detector.
- The BP at 0x476C (title-screen SPACE check seen in old analysis) is **never
  reached** in normal play. The real SPACE check happens at 0x424C, called
  from 0x41DB → 0x4042 → init path.
- `debug running` is not a valid openMSX TCL subcommand. Use `debug breaked`.
- Calling `cont()` on an already-running CPU silently succeeds (no error, no
  effect). Always check `debug breaked` before calling `cont()`.

### 6. New / updated tool files

- `tools/zanackb/openmsx.py` — added `MSXKey` constants, `key_down/up/press`,
  `keys_down/up`, `release_all_keys`, `set_watchpoint`, `remove_watchpoint`,
  `poll_flag`, `read_vram`, `read_name_table`, `is_running`, `read_byte`,
  `write_byte`
- `tools/zanackb/zanac_game.py` (new) — `ZanacGame` controller class with
  `launch()`, `attach()`, full screen-state detection, ship control, and
  event detectors

### Test results

| Step | Result |
|---|---|
| Fresh headless launch → title screen | 1.0s ✓ |
| `start_game()` via SPACE injection | ✓ (lives=3, ZANAC visible) |
| `steer(up=True)` + `shoot_both()` | Ship moves and fires ✓ |
| Kill detection (score watchpoint) | 3 kills, score=18 ✓ |
| Collision detection (lives watchpoint) | lives 3→2→1 detected ✓ |
| STOP key pause/unpause | ✓ |
| GAME OVER detection | ✓ |
| `skip_to_title()` (SPACE from game-over) | ✓ |
| Second `start_game()` cycle | ✓ (lives=3 again) |

### Next sprint candidates

- **0018 — Fire weapon projectile system**: trace type-3 handler at 0x7253;
  map fire weapon types 1–7 to their entity types, sprites, and behavior.
- **0018b — Spawn table source**: what writes 0xE133 to advance the level
  sequence (carry-over from sprint 0016 proposal).
