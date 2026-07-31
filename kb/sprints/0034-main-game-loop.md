---
id: "0034"
status: done
range: 0x4002-0x4002,0x4042-0x41DB
strategy: forward_from_caller
budget_turns: 20
---

# Sprint 0034 — Main game loop dispatch and state handlers

## Goal

Document the top-level game loop that dispatches on `E102` flags each frame,
and all the handler stubs it calls that are currently undocumented:

1. **`LAB_4042`** (0x4042) — title-restart entry: resets enemy state, plays title
   music, arms keyboard, then falls into the main frame loop.
2. **`LAB_4074`** (0x4074) — per-frame gameplay dispatch: calls `scroll_velocity_ctrl`,
   `sub_8f5e`, `gameplay_frame_loop`, `game_over_handler`, `sub_bf2c`; then tests
   E102 bits 5/3/7/4/6 to branch to level-complete, credits, title, timer, respawn.
3. **`SUB_40BA`** (0x40BA) — `reset_entities`: zeroes entity slots 1–21 (skips
   slot 0 = player), clears E150/E132 (boss-active / scroll mode flags).
4. **`LAB_40DA`** (0x40DA) — level-complete handler: resets entities, loads next
   level's tile set, plays music, runs 100 transition frames.
5. **`LAB_412A`** (0x412A) — `load_bg_level`: calls `reset_enemies_and_psg`,
   `decompress_block`/`load_bg_tiles` for the new stage.
6. **`SUB_41BA`** (0x41BA) — display-timer countdown: decrements E15E; when it
   reaches 0, clears E102 bit 4 (exits the title-screen timer).
7. **`INIT`** (0x4002) — ROM header init-entry word: a `DW 0x4010` pointer in
   the standard MSX cartridge header (data entry, not a routine).

## Inputs

- `kb/guides/input-state-machine.md` — E102 bit map (all 8 bits)
- `kb/symbols/0x4000-init/game_over_handler.md` — how LAB_4074 calls it
- `kb/symbols/0x4000-init/gameplay_frame_loop.md` — called with B=1 each frame
- `kb/symbols/0x4000-init/wait_one_frame.md` — 0x4306, used by LAB_40A8 respawn loop
- Source lines 54–260 (`LAB_4042` → `SUB_41ba` and surrounding context)

## Verification plan

### Step 1 — Static trace of LAB_4042 and LAB_4074 (static)

Read source lines 54–130.  Map the full call graph from LAB_4042 through
LAB_4074, noting which branches lead to each handler.  Confirm:
- How `sub_8f5e` relates to the scroll engine (hypothesis: it calls the scroll
  pipeline — scroll_map_reader + scroll_vram_write).
- How `sub_bf2c` relates to the encounter system (hypothesis: it calls
  base_encounter_ctrl and ground_struct_spawn_ctrl).
- The exact flow when E102 bit 6 (respawn) is set: the 64-frame `LAB_40A8`
  loop runs `scroll_velocity_ctrl` + `sub_8f5e` + `gameplay_frame_loop` × 64,
  then jumps to `LAB_4068` to reinit entity slot 0.

### Step 2 — Decode SUB_40BA (static)

Read source lines 105–120.  Confirm it iterates IX from 0xE3A0 (slot 1),
stepping by 0x20, for 21 iterations; AND-masks slot[0] with 0x7F (preserves
high bit), and if non-zero sets to 0x28 (entity type 0x28 = "fade out").
Confirm E150 and E132 are zeroed.

### Step 3 — Decode LAB_40DA and LAB_412A (static)

Read source lines 121–170.  Confirm:
- The branch at 0x40E2 (JP Z, LAB_414d) selects between a "same-stage" path
  (level_stream_ptr == 0 → skip tile reload) and the "new-stage" path.
- LAB_412A calls `reset_enemies_and_psg` + two tile loaders + plays music event.

### Step 4 — Decode SUB_41BA (static)

Read source lines 235–270.  Confirm the countdown mechanic for E15E and which
writes transition from the title-timer state.

## Key questions

- What entity type 0x28 means when assigned by `reset_entities` — is it a
  "dying" type that gets one more frame before clearing to 0?
- Does `sub_8f5e` call the entire scroll pipeline, or only the VRAM write half?
- What is `sub_bf2c` — is it the encounter/base-spawn dispatcher for one frame?

## Expected KB entries

- `kb/symbols/0x4000-init/title_restart.md` — `LAB_4042` / `LAB_4074` combined
  (or separate files if sufficiently distinct)
- `kb/symbols/0x4000-init/reset_entities.md` — `SUB_40BA` (0x40BA)
- `kb/symbols/0x4000-init/level_complete_handler.md` — `LAB_40DA` (0x40DA)
- `kb/symbols/0x4000-init/load_bg_level.md` — `LAB_412A` (0x412A)
- `kb/symbols/0x4000-init/display_timer_countdown.md` — `SUB_41BA` (0x41BA)
- `kb/data/rom_header.md` update — note that 0x4002 is the `INIT` DW pointer

## Summary (filled at end)

Static decode of the top-level game loop and its frame handlers (0x4042–0x41DB).
Builds directly on sprint 0033, which already traced `LAB_40DA`/`LAB_412A` for
the credits logo.

### New symbols
- `main_game_loop` (0x4042 + 0x4074) — restart-init head + per-frame dispatcher
  (the sprint's `title_restart`, renamed to its true function).
- `reset_entities` (0x40BA) — fade non-player entities to type 0x28; clear E150/E132.
- `level_complete_handler` (0x40DA) — stage→stage transition (canonical range
  0x40DA–0x4129; shared tail 0x413A–0x4162 documented inline).
- `load_bg_level` (0x412A) — the `stage & 7 == 0` load path (bg tiles +
  `load_logo_tiles`).
- `display_timer_countdown` (0x41BA) — E15E countdown that clears E102 bit 4;
  documents the shared helper `sub_41cb` (0x41CB).
- Updated `rom_header` — 0x4002 is the INIT `DW 0x4010` data pointer, not code.

### Key-question answers
- **Entity type 0x28** = a transient "fade-out / leaving" type assigned to live
  non-player entities at a level transition. Confirmed it is special-cased:
  `explode_enemies` (0x8A26) excludes 0x28 when converting enemies to
  explosions. (Exact per-frame animation not yet traced → hypothesis.)
- **sub_8f5e (0x8F5E)** is NOT the tile pipeline — it is the base/boss
  **encounter scroll-mode controller**: dispatches on `E150`
  (`base_encounter_flags`) to 0x934D/0x9028 and ramps `E710` (scroll speed) via
  the table at 0x8F9A as a structure/boss is approached. The per-frame tile
  pipeline is `gameplay_frame_loop` (sub_9393) + the VBLANK `scroll_vram_write`.
- **sub_bf2c (0xBF2C)** is the **timed spawn-script ticker**: advances the
  E137/E138 countdown timers, indexes the spawn table at `(0xE133)` by counter
  `(IX+0x26)`, and spawns each due entity via 0x4496; returns early during the
  end-credits (E102 bit 3).

### Flow confirmed
- `LAB_4074` dispatch order: `scroll_velocity_ctrl` → `sub_8f5e` →
  `gameplay_frame_loop` → `game_over_handler` → `sub_bf2c` → E102 branch
  (bit 5 → level-complete, 3 → credits, 7 → title, 4 → display timer,
  6 → 64-frame respawn loop `LAB_40A8` → `LAB_4068`).
- Validation clean: 285 entries, 0 errors.
