---
id: "0032"
status: done
range: 0x4343-0x43D9,0x75D5-0x7822,0x7221-0x7252,0x7253-0x72FF
strategy: forward_from_caller
budget_turns: 30
---

# Sprint 0032 — Gameplay key handling: movement, shot, fire weapon, pause

## Goal

Fully decode how keyboard and joystick input drives the player ship during
active gameplay, covering:

1. **Player-ship motion** — how E10C (X-velocity computed by `sub_4343`) is
   consumed by the type-1 handler (0x75D5) to move the sprite each frame.
   Confirm whether the player also reads E100 bits directly or only E10C.

2. **Shot spawn trigger** — exactly when and how pressing SHIFT or SPACE
   (E100 bit 4 = 0) spawns a type-2 entity.  Find the shot-spawn call site,
   the slot-allocation guard (E10D = max simultaneous shots), and confirm
   which entity slots are reserved for shots (expected: slots 1–4).

3. **Fire-weapon spawn trigger** — when and how Z or SPACE (E100 bit 5 = 0)
   spawns a type-3 entity.  Identify the fire-weapon slot (expected: slot 4),
   the cooldown / active-check guard, and how `fire_type` (0xE14B) selects
   the weapon variant.

4. **Pause / STOP key** — identify where the STOP key (or equivalent) is
   polled during gameplay and what flag it sets.  Candidate: E102 bit 6 is
   cleared each frame but set by something — confirm whether that's the pause
   flag and which key sets it.

5. **Any undocumented in-game key combos** — look for any checks on row 7,
   row 3, or uncommon rows beyond the six known (rows 5, 6, 8) to find cheat
   codes, debug toggles, or hidden functions.

6. **Joystick vs keyboard equivalence** — confirm that E100 bits 6–7
   (joystick port B triggers from PSG) are used identically to bits 4–5 for
   shot and fire-weapon spawning during gameplay.

## Inputs

- `kb/guides/keyboard-input.md` — E100 layout, `sub_4343` (0x4343), `sub_46bc` (0x46BC)
- `kb/data/entity_table.md` — entity slot 0 (player), slots 1–4 (shots)
- `kb/symbols/0x5000-gameplay/` — shot system, fire weapon system (sprints 0016, 0023)
- `kb/sprints/0016-shot-system.md` — shot SAT_NAME / vy from 0xE10E–0xE10F
- `kb/sprints/0023-fire-weapon-system.md` — fire_type at 0xE14B

## Verification plan

### Step 1 — Trace player handler motion (static)

Read source around the type-1 handler (0x75D5, ~source line 3544).  Answer:
- Does it call `sub_4343` directly, or does it rely on E10C being pre-computed
  by the game loop's own `sub_4343` call?
- What is the exact update sequence: read E10C → clamp → update IX+0x02 (X)?
- Is vertical motion (Y) also key-driven, or only scroll-driven?

### Step 2 — Find shot spawn call site (static + live)

Search the type-1 handler (0x75D5) and nearby routines for:
- A check on E100 bit 4 (`BIT 4, (hl)` or `AND 0x10; JR Z`)
- A call to `find_free_slot` (0x4496) scoped to slots 1–4
- A `LD (IX+0x0), 0x02` (set entity type = shot)

Live probe: set a write-watchpoint on entity slot 1 type byte (0xE320), fire
SHIFT, capture the caller PC.

```python
with ZanacGame.launch() as game:
    msx = game.client
    game.wait_for_title(); game.start_game()
    time.sleep(0.5)
    msx.cmd("set ::shot_pc 0")
    wp = msx.cmd("debug set_watchpoint write_mem 0xe320 "
                 "{[debug read memory 0xe320] == 0} "
                 "{set ::shot_pc [reg PC]; debug break}")
    game.fire_shot(duration=0.05)
    time.sleep(0.3)
    pc = msx.cmd("set ::shot_pc")
    msx.remove_watchpoint(wp)
    print("Shot spawned by PC:", hex(int(pc)))
```

### Step 3 — Find fire-weapon spawn call site (static + live)

Same approach for type-3 entity (fire weapon projectile).  Watch slot 4 type
byte (0xE380).  Expected spawn PC is somewhere in the type-1 handler body.

### Step 4 — Identify STOP / pause key

Search source for SNSMAT calls on rows other than 5, 6, 8.  Grep:
```bash
grep -n "CALL.*0141\|0x0141" source/zanac-02.asm
```
For each, note the row number (the `LD A, N` immediately before).  Any row
not yet in the KB is a new key.

Live probe: break at every SNSMAT call found above, record PC and row number
during active gameplay.

### Step 5 — Undocumented key combos

For every SNSMAT call found in Step 4, trace what the returned value is used
for: which bits are tested, what flags/variables they write, and whether any
combination is conditionally activated.  Pay special attention to:
- Rows 3–4 (function keys, ESC area in some layouts)
- Any `CP 0xFF` or `AND 0xFF; RET NZ` style "all-keys-released" guard that
  might gate a debug sequence

### Step 6 — Joystick port B in gameplay (static)

Re-read `sub_4343` (0x4343).  The two PSG reads produce E100 bits 6–7 from
port B.  Confirm: are these bits tested in the shot or fire-weapon spawn code
the same way bits 4–5 are?  Or are bits 6–7 ignored in gameplay?

## Key questions this sprint should answer

- Which instruction spawns a shot, and at what address?
- Which instruction spawns a fire-weapon projectile?
- Is there a PAUSE key, and what does it set in E102?
- Are there any SNSMAT calls on rows other than 5, 6, 7, 8?
- Are joystick port B triggers equivalent to keyboard fire during gameplay?
- Is there any "hold N keys simultaneously" cheat reachable from the keyboard?

## Summary (filled at end)

All six SNSMAT call sites mapped (rows 5, 6, 7, 8 only — no hidden rows).
Full per-state key handling documented in `kb/guides/input-state-machine.md`.

### Key questions answered

**PAUSE key**: STOP (row 7, bit 4) via `sub_4da5` (0x4DA5), called every
frame from `sub_9393`. Sets no E102 bit; creates a blocking inner loop that
freezes entity dispatch and scroll. SELECT (row 7, bit 6) also exits the pause.

**E102 flag map**: documented (bits 0–7).  STOP does NOT set any E102 bit;
it blocks internally inside `sub_4da5`.

**SNSMAT rows used**: 5, 6, 7, 8 only.  No rows beyond these were found.

**Joystick port B**: PSG register 14 bits 6–7 map to E100 bits 6–7 after
two ANDed reads.  `sub_46bc` tests only bits 4–5 (`AND 0x30`), so port-B
triggers (bits 6–7) do **not** advance through the standard fire-detect path.

**Undocumented combos**:
- SELECT (row 7 bit 6) has an observable effect only inside STOP-pause.
- ESC (row 7 bit 2) works as continue-from-last-round at title AND as
  exit-to-title during the game-over weapon-selection timeout.
- No hidden row-reads or multi-key sequences found beyond the above.

**Shot/fire spawn**: not traced to exact address this sprint (deferred to
a dedicated shot-system sprint). `sub_4343` → E100 bits 4,5; the player
handler at 0x75D5 consumes these. Shot slots: entity slots 1–4.

### New KB entries

- `kb/guides/input-state-machine.md` — per-state key table, E102 bit map,
  game-over sequence flow, PAUSE inner-loop mechanics.
- `kb/symbols/0x4000-init/player_hit_handler.md` — 0x4649, decrement lives, set respawn/game-over flag.
- `kb/symbols/0x4000-init/game_over_handler.md` — 0x4663, save hiscore, "GAME OVER" display, 800-frame wait.
- `kb/symbols/0x4000-init/wait_fire_or_timeout.md` — 0x46A8, game-loop wait with fire-skip.
- `kb/symbols/0x4000-init/fire_edge_detect.md` — 0x46BC, rising-edge detect for fire keys/joystick port A.
- `kb/symbols/0x4900-hud/score_display_update.md` — 0x4AA5, flush dirty score BCD to VRAM.
- `kb/symbols/0x4900-hud/update_fire_display.md` — 0x4DA5, **corrected** from sprint-0002 hypothesis; actual function is `pause_handler` (STOP/SELECT blink loop).
- `kb/symbols/0x9000-scroll/gameplay_frame_loop.md` — 0x9393, B-frame loop: VBlank sync + pause + score + entity dispatch + hit check.
