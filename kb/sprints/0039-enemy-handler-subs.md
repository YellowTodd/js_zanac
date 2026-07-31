---
id: "0039"
status: done
range: 0x7A67-0x7A67,0x816D-0x816D
strategy: forward_from_caller
budget_turns: 15
subsystems: [G]
---

# Sprint 0039 — Enemy handler sub-routines: base-spawner active state and projectile fire sub

> **Subsystem slice:** [[G-enemy-and-spawn-system]] — close 0039 when the G
> enemy-handler slice develops (`LAB_7A67` base-spawner active state,
> `LAB_816D` `fire_ground_projectile`).

## Goal

Document two enemy handler sub-routines that are called by already-documented
symbols but have no KB entries:

1. **`LAB_7A67`** (0x7A67) — called by `handler_type11_base_spawner` (0x7548).
   The base-spawner handler is a two-phase state machine:
   - Init phase (first call, BIT 7 clear): sets entity parameters, sets BIT 7.
   - Active phase (subsequent calls, BIT 7 set): entered at `LAB_7A67`.
   This address is the "already initialized" branch — it runs the base's frame
   logic: tracking, firing, and health management each game frame.

2. **`LAB_816D`** (0x816D) — called by `handler_type46_ground_projectiles`.
   From the ASM context, 0x816D is reached after `entity_update` and `0x71F6`
   are called at 0x8164/0x8167.  It sets IX+0x03 = 0x4C (changes own sprite
   to "muzzle flash" tile 0x4C), then allocates a child entity slot via
   `alloc_entity_slot` (0x4496) and dispatches to the child-init path at 0x8DDB.
   Hypothesis: `fire_ground_projectile` — the sub-routine that creates the
   bullet entity and initialises it.

## Inputs

- `kb/symbols/0x8000-enemy/handler_type11_base_spawner.md` — calls 0x7A67
- `kb/symbols/0x8000-enemy/handler_type46_ground_projectiles.md` — calls 0x816D
- `kb/symbols/0x4000-init/alloc_entity_slot.md` — called by 0x816D
- Source lines 4390–4450 (0x7A67 area inside handler_type11 block)
- Source lines 5140–5190 (0x816D area inside handler_type46 block)

## Verification plan

### Step 1 — Decode LAB_7A67 (static)

Read source lines 4398–4480.  Map:
- Does the active-state code loop back to a common exit (entity_post at 0x48D0)?
- Which registers does it modify (IX+0x18/0x19 appear at 0x7A70/0x7A76 — health
  or position fields)?
- Is there a nested state machine (another BIT test within the active phase)?

### Step 2 — Decode LAB_816D (static)

Read source lines 5146–5190.  Confirm:
- That IX+0x03 = 0x4C is the sprite change ("muzzle flash").
- That `alloc_entity_slot` at 0x817C is the child allocation.
- What parameters are set on the child slot (type byte, velocity, etc.).
- How the code at 0x8DDB initializes the child (likely sets child type = bullet).

## Key questions

- Does `LAB_7A67` share structure with any other "active-state" branch in the
  0x7548–0x86FF handler block, or is it unique to type 11?
- Does `LAB_816D` reuse `alloc_entity_slot` the same way `spawn_col_marker`
  does (call 0x4496, check carry, initialize IX result)?
- What entity type does 0x816D assign to the spawned child?

## Expected KB entries

- `kb/symbols/0x8000-enemy/base_spawner_active.md` — `LAB_7A67` (0x7A67)
- `kb/symbols/0x8000-enemy/fire_ground_projectile.md` — `LAB_816D` (0x816D)

## Summary

Closed across the G slices: **`LAB_7A67`** documented as
[[base_spawner_active]] (0x7a67) in sprint 0049; **`LAB_816D`** documented as
[[fire_ground_projectile]] (0x816d) in sprint 0051. Both live-confirmed.
