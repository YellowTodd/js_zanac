---
id: "0035"
status: done
range: 0x44D4-0x45A0,0x4898-0x48D0,0x46D9-0x46D9
strategy: forward_from_caller
budget_turns: 20
---

# Sprint 0035 — Entity slot internals: post-update, collision, and credits entry

## Goal

Document the sub-routines inside the 0x44xx–0x48xx entity-slot block that are
referenced by already-documented symbols but have no KB entries:

1. **`entity_post` helpers** (0x44D4, 0x44F9) — called by both `collision_routine`
   and `entity_post`.  Hypothesis: handle per-slot bookkeeping after position
   update and before sprite-shadow write (clamp, sprite-type select, SAT write).
2. **`LAB_453E`** (0x453E) — mid-point in the entity loop, possibly the per-slot
   "skip inactive" branch or the dispatch to a sub-type-specific post-handler.
3. **`collision_check`** (0x45A0) — entry to the collision check sub-routine;
   called by `entity_post`.  Expected to compare IX-slot bounding box against
   the player bounding box using E129/E12A (player X/Y snapshot).
4. **`entity_update`** (0x4898) — per-slot X/Y position integrator; reads
   IX+0x02/0x03 (vx, vy) and adds to IX+0x0A/0x0B (X, Y).  Shared by most
   active entity types.
5. **`sprite_shadow_push` helper** (0x48B8) — entered after `sprite_shadow_push`
   (0x48A9); writes SAT name/colour byte to the VRAM shadow at `(E122)`.
6. **`LAB_46D9`** (0x46D9) — end-credits entry; called from the main game loop
   when E102 bit 3 is set.  Sets IX+0x5C=0, calls `compare_save_hiscore`, then
   runs the credits display loop (staff names, fire-to-cycle, ESC-to-title).

## Inputs

- `kb/symbols/0x4000-init/entity_dispatch.md` — 0x445F dispatcher architecture
- `kb/symbols/0x4000-init/entity_post.md` — existing partial entry (collision_routine, entity_post)
- `kb/symbols/0x4000-init/collision_routine.md` — calls 0x44D4
- `kb/symbols/0x4900-hud/player_pos_snapshot.md` — E129/E12A bounding box
- `kb/guides/input-state-machine.md` — end-credits display loop narrative
- Source lines 600–1060 (0x44D4–0x48D0 range)
- Source lines 928–932 (0x46D9 = LAB_46d9 context)

## Verification plan

### Step 1 — Trace entity_post helpers (static)

Read source lines 600–660 (0x44D4–0x44FF area).  Determine what `entity_post`
calls at 0x44D4 and 0x44F9 — are these two entry points into the same routine,
or distinct helpers?  Map their register usage.

### Step 2 — Trace LAB_453E (static)

Read source lines 648–720 (0x453E–0x45A0).  Confirm whether this is the start
of the collision-check inner loop or a type-dispatch branch.

### Step 3 — Trace collision_check and entity_update (static)

Read source lines 712–750 (0x45A0 area) for `collision_check`.
Read source lines 1030–1060 (0x4898 area) for `entity_update`.
Confirm the bounding-box comparison algorithm and the X/Y integration step.

### Step 4 — Trace sprite_shadow_push helper (static)

Read source lines 1042–1055 (0x48B8 area).  Confirm what `sprite_shadow_push`
does at `LAB_48B8` vs the main entry at 0x48A9.

### Step 5 — Trace LAB_46D9 (credits entry) (static)

Read source lines 928–945 (0x46D9 area).  Map the full credits display loop
through the `wait_fire_or_timeout` calls and the ESC-to-title path.

## Key questions

- Are 0x44D4 and 0x44F9 separate entry points to the same finalization routine
  (e.g. skipping sprite-shadow write vs including it)?
- Does `entity_update` handle screen-edge clamping or is that done elsewhere?
- Is `LAB_46D9` a separate named routine, or just a continuation of the
  game-over handler that falls through after the game-over wait?

## Expected KB entries

- `kb/symbols/0x4000-init/entity_finalize.md` — helpers at 0x44D4/0x44F9 (one
  or two files depending on whether they're entry points to the same routine)
- `kb/symbols/0x4000-init/collision_check.md` — 0x45A0
- `kb/symbols/0x4000-init/entity_update.md` — 0x4898
- `kb/symbols/0x4000-init/sprite_sat_write.md` — 0x48B8 helper
- `kb/symbols/0x4000-init/credits_display.md` — `LAB_46D9` (0x46D9)
- Update `entity_post.md` with cross-refs to new entries

## Summary (filled at end)

All six targets decoded statically; `zanackb validate` clean (0 errors).

### Findings

1. **0x44D4 and 0x44F9 are two distinct collision-target dispatchers**, not
   finalization helpers and not two entry points to one routine. Documented in
   `collision_dispatch.md`:
   - `check_hit_player` (0x44D4): tests IX vs the player ship (E300, type 0x81)
     and the ground target (E380, type 0x83, gated by E14E bit 0). Sub-entry at
     0x44EA does player-ship-only.
   - `check_hit_shots` (0x44F9): tests IX vs the three player-shot slots
     (E320/E340/E360, type 0x82) and the ground target (gated by E14E bit 1).
   Both call the `collision_check` primitive at 0x4560 and return carry on hit.
   Slot/type map (E300=ship 0x81, E320/40/60=shots 0x82, E380=ground 0x83) and
   E14E as the collision-enable mask are confirmed from the code.

2. **LAB_453E = `collision_response`** (`collision_response.md`): on a hit it
   remaps **both** colliding entities' type bytes through the transition table
   at **0x716B** (→ explosion/despawn type) and saves the current entity's
   original type to `IX+0x18`. This is the real owner of the `LD HL,0x716B`
   instructions that sprint 0021 mis-attributed to 0x4560. Sprint 0030's live
   trace (IX=ground struct, IY=player shot) lands exactly here.

3. **`collision_check` (goal #3) was already documented.** The sprint listed it
   at 0x45A0, but 0x45A0 is `hitbox_setup_ix` and the actual check is at 0x4560
   — both already covered by `collision_routine.md` (sprint 0030). No duplicate
   created; cross-refs added instead.

4. **`entity_update` (0x4898)** (`entity_update.md`): homing dispatcher driven by
   `IX+0x0C` behaviour flags (bit3=Y-homing, bit4=X-homing), then **falls
   through** into `sprite_shadow_push`. Position is 16-bit fixed point:
   Y int/frac/vel at IX+0x01/0x06/0x08:09, X at IX+0x02/0x07/0x0A:0B. Off-screen
   despawn (Y≥0xD0 → `entity_clear` 0x48D0) happens inside the motion subs. The
   sprint's hypothesised field layout (vx/vy at +0x02/+0x03) was wrong.

5. **Split the conflated `sprite_shadow_push.md`.** The old entry (addr 0x48A9)
   actually decoded the 0x48B8 SAT-write tail. Now:
   - `sprite_shadow_push.md` (0x48A9) = linear-motion + animation dispatch
     (BIT 0/1/2 of C), reached only by fall-through from `entity_update`.
   - `sprite_sat_write.md` (0x48B8) = the 4-byte SAT-shadow append via E122;
     also a genuine `JP` target from three handlers (0x73C5/0x83F2/0x8443).

6. **LAB_46D9 = `credits_display`** (`credits_display.md`): a standalone staff-
   roll routine, not a fall-through from the game-over handler. Sets E15C=0,
   calls `compare_save_hiscore` (0x4ACE — confirmed: 3-byte E103 vs E106 compare
   + copy-up), then runs the page loop (control table 0x4775, length-prefixed
   strings 0x47AA), fire-to-cycle via 0x46A8, ESC→title via check_start_key
   (0x43D2) → 0x4042. Full key narrative already in `input-state-machine.md`.

7. **Corrected `entity_post.md`**: the `CALL 0x45A0` is `hitbox_setup_ix`, not a
   sprite-shadow push; rewrote the analysis annotations and added cross-refs.

### KB entries

- NEW: `collision_dispatch.md`, `collision_response.md`, `entity_update.md`,
  `sprite_sat_write.md`, `credits_display.md`
- UPDATED: `sprite_shadow_push.md` (repurposed to 0x48A9 motion dispatch),
  `entity_post.md` (corrections + cross-refs, sprint bump)
- NOT created: `collision_check.md` (0x45A0/0x4560 already in
  `collision_routine.md`); `entity_finalize.md` (renamed to
  `collision_dispatch.md` — the helpers are collision dispatch, not finalize)

### Follow-ups

- Document the **death/collision transition table at 0x716B** ([[death_transition_table]]).
- Document **`compare_save_hiscore` (0x4ACE)** as its own entry (out of range here).
