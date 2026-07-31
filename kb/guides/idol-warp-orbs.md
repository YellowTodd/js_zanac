---
name: idol-warp-orbs
description: "The totem → orb → kill-all/warp mechanic: shooting a ground totem (wide structure) spawns a floating type-72 eraser orb; touching it yellow kills all enemies, touching it black warps to a round encoded in the per-round table at 0xE720. Type-71 = smiling totem (specific-round warp), type-70 = plain totem (round-0 'invisible totem'), type-82 = fire-powerup box. Per-round census + round-0 recipe."
kind: guide
confidence: confirmed
sprint: "0061"
tags: [secrets, warp, orb, idol, base, entity, map-data, e720, subsystem-m]
---

# Idols, orbs & warps

Zanac's mid-game **warp** feature (subsystem [[M-secrets-and-warps]]). Shooting a
ground **idol** eventually releases a floating **orb**; touching it either wipes
the screen of enemies or **teleports the player to another round** — including an
earlier one. This guide documents the whole chain and catalogues the warp
destinations encoded per round.

> **KB correction (0059):** [[handler_type72_base_core]] (type 72) was framed as
> a "base core" whose destruction "advances round progress". It is actually the
> **orb**: a floating pickup whose *player-touch* effect is kill-all-enemies
> (yellow) or **warp** (black). What looked like "round advance" is the warp
> path. Live-confirmed (`tools/sprint0059_verify.py`).

## The two entities

| Role | Entity | Handler | Sprite |
|------|--------|---------|--------|
| **Idol / totem** (ground construction) | wide ground-structure, types 70–71, 81, 87–89 | [[handler_type70_wide_structure]] (0x87AB) | multi-tile wall/statue. **Type 71 = smiling totem** (specific-round warp); **type 70 = plain totem** (→R0 / normal). *Type 82 = fire-powerup box, not a totem — see below.* |
| **Orb** (floating pickup) | type 72 (0x48) | [[handler_type72_base_core]] (0x8983) | pattern 0x24 = **large circle**, color 0x8A; drifts slowly upward (vy≈−0.03) |

The idol takes hits through the box hit-sub (0x7904); its HP is `(IX+0x19)`, set
from the spawn Y-band (6/3/4 hits). It is not destroyed by a single shot — you
must "shoot it many times". When HP reaches 0 the handler **re-types the same
slot to 0x48 (orb)** at 0x8810 and branches by the idol's sub-type `(IX+0x18)`
(see *Conditions* below).

## Visual identification — the "smiling face" idol

Warp-releasing idols are **visually distinct** — a black-and-white / grey
"**smiling face**" construction (player-observed, screenshot-confirmed sprint
0060: `tools/sprint0060_shot.py` broke exactly as the round-2 → round-1 warp idol
initialised and captured a grey face object at its position, top row / X≈200).

**They are entity type 71.** The per-round idol census (below) shows every
real-round warp destination is carried by a **type-71** structure; the other
wide-structure types (70/81/82/87–89) carry small `+0x1C/1D` values (→ round 0)
or tile/displacement data. The distinct look comes from the **background tile
graphics** placed for a type-71 idol, not from an entity-handler foreground draw.

> **Correction (0060/0061):** sprint 0059 guessed the marker was type **82** via
> its `0xD2` foreground-tile branch in [[handler_type70_wide_structure]]. That was
> **wrong** — type 82 is not a totem at all but the **fire-powerup box** (the
> `0x30 + (IX+0x1C)` glyph is the **fire-weapon digit**; see the fire-dispenser
> section below). The real warp idols are **type 71**, which does *not* run the
> 0xD2 draw (types 70/71 → HP 6, skip to post-handling).

## Orb state machine (type 72)

```
spawn:   (IX+0x1E) = 4      ; "yellow" life counter
         (IX+0x1C/1D)       ; inherited from the idol = WARP DESTINATION (stream ptr)
each active tick: when the (IX+0x1B) sub-timer underflows, (IX+0x1E)--        ; 4→0 = yellow→BLACK
         while (IX+0x1E) != 0 the orb can also self-despawn (timeout path)
         once (IX+0x1E) == 0 the countdown/timeout is skipped → BLACK orb persists

player touch  (collision check 0x44B0 vs player slot 0xE300, type 0x81):
   (IX+0x1E) != 0  (YELLOW)  → explode_enemies (0x8A26) = KILL ALL ENEMIES + SFX 0x13
   (IX+0x1E) == 0  (BLACK)   → E722 = (IX+0x1C/1D) ; set E102 bit 5 (level_complete)
                               → level_complete_handler → resolve_round_from_ptr
                               → E701 = destination round ; reload that round
```

So **every** orb starts yellow (screen-clear bomb) and turns black if you don't
collect it in time; the black orb is the **warp orb**. The destination is fixed
by the idol that spawned it.

### Why E722 → a round

`resolve_round_from_ptr` (0x9444) walks [[stage_stream_ptr_table]] (0x945C) and
returns the round (1–8, or 0) whose stream-start the pointer is ≥. So the orb's
`+0x1C/1D` must be a **stream pointer** in 0xA65C–0xB7A5; a value below round 1
(e.g. tile-data 0x9Bxx or a small random) resolves to **round 0** (the secret
stage, see [[M-secrets-and-warps]]).

## Data flow — where the destination comes from

1. Each round's **map script** runs **command 8** ("ROUND n" banner) at round
   start; its 2-byte operand is stored to **0xE720** ([[level_script_format]],
   handler 0x9699). This points at the round's **idol table** (tail of the
   round's script data).
2. When an idol activates, [[handler_type70_wide_structure]] reads
   `(0xE720)[(IX+0x03)]` and `[+1]` into `(IX+0x1C/1D)` (source 0x87B0–0x87C0).
   `(IX+0x03)` is the idol's per-instance table index (from its spawn record);
   it is then overwritten with the tile pattern 0x24.
3. The orb inherits `+0x1C/1D` when the slot is re-typed to 72.

The 0xE720 idol table is a packed structure: a header of idol parameter/pointer
records, followed by an index list `02 04 06 01 03 05 07` and `00 8x …`
wide-structure Y/X/tile records. **Warp destinations are the stream-range
pointers (0xA6xx–0xB7xx) in the header.**

## Per-round warp-idol census (live-confirmed, sprint 0060)

`tools/sprint0060_census.py` warps to each round, runs at max speed with the ship
invincible, and logs every wide-structure init at 0x87C3 — capturing the idol's
**type**, **`+0x03`** table index, resulting **`+0x1C/1D`** and the **live E701**
(so idols are attributed to the round they actually spawn in). All specific-round
warp idols are **type 71**:

| Round | E720 table | Type-71 warp idols (idx → dest → round) | Backward? |
|-------|-----------|-----------------------------------------|-----------|
| 0 | 0xA6EC | *(none — secret round; only type-82 fire boxes)* | — |
| 1 | 0xAA68 | idx 6 → 0xAAEF → **R2** | forward |
| 2 | 0xAD33 | idx 2 → 0xA751 → **R1**; idx 4 → 0xAD4B → R2; idx 14 → 0xAD61 → **R3** | **R2→R1 ↩** |
| 3 | 0xAF09 | *(none)* | — |
| 4 | 0xB1BF | *(none)* | — |
| 5 | 0xB3F5 | idx 1 → 0xAF1F → **R4**; idx 3 → 0xB3FD → **R6** | **R5→R4 ↩** |
| 6 | 0xB604 | *(none)* | — |
| 7 | 0xB787 | idx 3 & 10 → 0xB7A5 → **R8** (advance); idx 6/12/20 → 0xB61A → **R7** (self-loop) | loop / advance |
| 8 | 0xB94C | *(none — final round)* | — |

- **Backward warps** — round **2 → 1** and round **5 → 4** — are the special warps
  to *earlier* rounds. Confirmed live: the idol's `+0x1C/1D` equals the earlier
  round's stream start, resolving through `resolve_round_from_ptr`.
- **Round 7 is a looping round.** Its idol table only offers **R7 (self)** and
  **R8**; the stage repeats until you either destroy the final base in time
  (→ R8) or take an R8 warp orb. (Player-reported; matches the census — R7's
  warp idols point only to 0xB61A=R7 and 0xB7A5=R8.)
- **Type-82 boxes** (small `+0x1C` = a fire-weapon digit) appear in every round —
  these are **fire-powerup dispensers**, not warp idols (see the fire section).
- **Round-0 totems**: idols whose `+0x1C/1D` resolves below round 1 warp to
  **round 0** — the "invisible totem" (census logged it as type-70 idx-88 =
  `0xA356`; mechanism corrected below — see *the warp-only re-entry stub*).
- Rounds 3/4/6/8 have **no** real-round (1–8) warp idols.
- The census counts total idol *activations* per round (≈30–60, incl. normal
  bases and re-spawns); the **warp idols** are the small type-71 subset above.

## Destruction sub-type → what a structure spawns (0x880D, decoded sprint 0061)

When a wide structure's HP hits 0, the handler branches on `(IX+0x18)` and
**overwrites the slot type** to decide what pickup it becomes:

| `+0x18` | Branch | Slot becomes | Meaning |
|---------|--------|--------------|---------|
| **< 0x51** (or 0x53) | 0x8833 | **type 72 = ORB** (+ spawns a type-81 child, base-encounter++) | the **eraser / warp orb** (kill-all / warp) |
| 0x51 | 0x8824 | type 0x50 (+ table 0x88C2) | structure part |
| **0x52** | 0x8874 | **type 0x53 = black-shadow (FIRE)**, SFX 0x12 | **fire-powerup dispenser** |
| 0x54–0x56 | 0x8854 | type 0x50 (+ table 0x88AB) | structure part |
| 0x57 | 0x8892 | type 0x50 (+ table 0x88B1) | structure part |
| 0x58 | 0x8892 | type 0x50 (+ table 0x88CB) | structure part |
| ≥ 0x59 | 0x88A2 | **type 0x53 = FIRE**, `(IX+0x1C)=R&7` | **random fire type** |

> **Correction (0061):** the `0x88A2` `LD A,R & 7` path was previously called a
> "random *warp* destination". It is a **random fire type** — it feeds `+0x1C`
> into the *fire* branch (0x8874 → type 0x53), not the orb. There is **no**
> random-warp mechanism. The only orb-spawning branch is `+0x18 < 0x51`.

## Conditions for releasing a warp orb

1. **Destroy the idol** — deplete its HP `(IX+0x19)` with shots and/or fire; its
   `+0x18` must be in the **orb range (< 0x51)** (the smiling/plain totems are).
2. **Let the orb turn black** — wait for `(IX+0x1E)` to count 4→0. A yellow orb
   only kills enemies; only the **black** orb warps.
3. **Touch it** with the ship (player-slot collision, 0x44B0). Its `+0x1C/1D`
   (from the round's 0xE720 table) becomes `E722` → the destination round.

## Reaching round 0 — the "invisible totem"

Round 0 is warped to by an orb whose `+0x1C/1D` **resolves below round 1**
(`< 0xA751` → `resolve_round_from_ptr` returns 0). Round 2 contains exactly such
an "invisible" totem, positioned **left of centre** near the round-2 start —
but **only after a warp re-entry**; it does not exist in a normal round-2 run
(see *the warp-only re-entry stub* below). Shoot it, let its orb blacken, touch
it → round 0. (The census logged it as type-70 idx 88 → `0xA356`, X≈64; the
probe observed type-71 idx 0 → `0xA65C`, X≈104 — see the corrections below.)

- **Live-confirmed (0061):** in round-2 play, forcing `E722 = 0xA356` + `E102`
  bit 5 → `E701 → 0`, round 0 loaded and playable (screenshot). This is the
  mechanic behind the player recipe below.
- Type 70 = plain/regular totem; **type 71 = smiling totem** (the visible
  specific-round warp idols). Both become orbs (`+0x18 < 0x51`); they differ in
  appearance and in which E720 index (→ destination) they carry.

### Search: is there a round-0 totem in any other round? (No)

All 9 rounds were swept with a **complete** live census (no early stop;
`tools/sprint0060_census.py`, ≥25 activations/round, round 7 = 260 over its
loops) looking for type-70/71 totems whose `+0x1C/1D` is a real map pointer
(≥ 0xA000) resolving to round 0. **Only round 2's idx-88 (`0xA356`) qualifies** —
it is the game's *unique* in-game gateway to round 0, which is why the recipe
routes through round 2.

> A **static** scan of the raw 0xE720 tables appears to show many "→R0" pointers
> in most rounds (e.g. 0xA2C9/0xA2EB/0xA744…), but these are **artifacts**:
> misaligned byte pairs and recurring non-pointer data past each table's real
> end. The live census (which reads the value a totem *actually* loads) confirms
> **no** type-70/71 totem uses them. Trust the census, not the raw-table scan.

## The warp-only re-entry stub (0xAD31–0xAD60) — why the invisible totem never appears in normal play

**Live-confirmed (2026-07-04, `tools/probe_idx88.py`); byte-exactly verified
sprint 0062** (`tools/decode_mapscript2.py`, grammar in
[[ground_structure_placement]] — the stub decodes cleanly as
`cmd6 E71C=33 · cmd8 idol_tbl=0xAD31 · cmd5 N=1 · cmd9→0xAAEF`, and a static
sweep confirms every mainline cmd-9 target is a real round entry, so this stub
is the *only* off-mainline re-entry). The invisible totem's placement records are
physically unreachable from round 2's normal script flow — it exists **only
after a warp**:

- **Round 2's normal script ends at 0xAD2E** with `89 61 AD` = cmd 9 →
  **0xAD61** (round 3's entry). A full normal-pass probe (idle ship, no
  shooting) confirms: the idx-2/4/14 smiling totems spawn, then the script jumps
  straight to round 3 — bytes **0xAD31–0xAD60 never execute** and no round-0
  totem ever spawns.
- The skipped region is a **warp-only re-entry stub**, reachable solely via the
  idx-4 smiling totem's black orb (dest = **0xAD4B**):

  ```
  0xAD31: 5C A6              alternate idol-table base — idx 0 → 0xA65C = ROUND 0 stream start
  0xAD33: …                  normal idol table (set by the preamble cmd 8 at 0xAAF9)
  0xAD4B: 00 00 86 33 32 00  stub entry (row trigger + cmd 6)
  0xAD51: 88 31 AD 32 00     cmd 8: "ROUND 2" banner again, but E720 = 0xAD31 (shifted −2!)
  0xAD57: 85 01 00 10 96 A3 32 00   cmd 5: one extra placement-stream slot (→ 0xA396)
  0xAD5E: 89 EF AA           cmd 9 → 0xAAEF: replay round 2 from its normal start
  ```

- On re-entry the secret totem spawns almost immediately (probe: type **71**,
  `+0x03` = **0**, row ≈101, X ≈104 — "down-middle, slightly left") **while
  E720 still points at 0xAD31**, so its table read yields idx 0 →
  **0xA65C = round 0's canonical stream start**. One record later the replayed
  preamble's own cmd 8 (0xAAF9) restores table 0xAD33 and the rest of the round
  plays normally (idx 2/4/14 spawn again with their usual destinations).
- End-to-end confirmation: simulating the orb touch (forcing E722 = 0xAD4B at
  the 0x40DD consumer in [[level_complete_handler]] + `E102` bit 5) reproduced
  the stub cmd 8 (E720 = 0xAD31 at script PC 0xAD51) and the round-0 totem
  spawn (dest = 0xA65C) in the same run where the preceding normal pass had
  produced neither.

### Corrections to the sections above

1. **The "idx 88 → 0xAD8B → 0xA356" attribution (0060/0061) is a census
   artifact.** The designed destination is **idx 0 through the shifted table
   0xAD31 → 0xA65C**. Both pointers resolve to round 0 (`< 0xA751`), so the
   earlier forced-`E722 = 0xA356` confirmation still "worked" — the warp is
   real, but its provenance was wrong.
2. **`(IX+0x03)` is not a fixed placement-record field.** Across probe runs the
   *same* script record (e.g. script PC 0xABE6) spawned structures with
   `+0x03` = 0, 28 and 88 — the index is assigned dynamically at spawn time
   (state/cursor still unidentified). Census idx values are therefore
   run-specific observations, not ROM constants; the type-71 idx 2/4/14 idols
   were stable across all probe runs, but treat every census idx with care.
3. The invisible totem was observed as **type 71** by the probe where the
   census had logged **type 70** — the type/idx assignment on this record is
   timing- or state-dependent. Pinning down what assigns `+0x03` (and the
   type byte) is a sprint-0062 target.

## Player recipe — skip to round 0 (external, mechanism-verified)

A player-reported route (untested by us end-to-end, but each step matches the
decoded mechanics):

1. **Round 1:** defeat the 1st and 2nd bosses; a *regular* totem then a *smiling*
   totem appear. Shoot the smiling totem → yellow eraser orb → wait for **black**
   → fly into it (warp; R1's smiling totem = idx 6 → R2).
2. **Round 2:** defeat the 1st boss; shoot the next smiling totem → it releases
   **two** eraser orbs → take the **2nd** to warp again (back into round 2).
3. When the **"ROUND 2"** title reappears, immediately fly **down-middle,
   slightly left** and shoot the **invisible totem** (spawned by the re-entry
   stub while E720 = 0xAD31; dest = `0xA65C`) → its black orb warps to
   **round 0**. Step 2's warp is what makes it exist at all: the totem's
   placement is exclusive to the 0xAD4B re-entry path.

## Fire-powerup dispensers (type 82) — not idols

The blue 4×4 ground boxes with a **digit** and a golden centre are **fire-weapon
dispensers**, not totems/idols. Entity **type 82** draws the digit
(`0x30 + (IX+0x1C)`, so `+0x1C` = the **fire-weapon number**) via the 0xD2 path
in [[handler_type70_wide_structure]], and on destruction (`+0x18 = 0x52`) spawns
a **type-83 black-shadow fire upgrade** ([[H-items-and-pickups]]). The two boxes
at the **start of round 1 show "2" and "1"** (fire types 2 and 1) —
screenshot-confirmed (`tools/sprint0060_shot.py`-style capture, sprint 0061).
They warp nowhere; earlier drafts mislabelled them "digit idols → round 0".

## Live confirmation (sprint 0059)

- **Orb effect tail** (`tools/sprint0059_verify.py`, micro-exec at 0x89EF):
  `+0x1E=0` (black), `+0x1C/1D=0xAD61` → `E722=0xAD61`, `E102` bit 5 **set**.
  `+0x1E=1` (yellow) → `E722` stays 0, bit 5 clear (kill-all path). ✓
- **E722 → round**: during round-1 play, writing `E722=0xB1DE` (round-5 stream)
  + `E102` bit 5 → `level_complete_handler` fired, `E701 → 5`, round 5 loaded. ✓
- **Per-round idol tables** live-read for all 9 rounds
  (`tools/sprint0059_e720.py`).

## Live confirmation (sprint 0061)

- **Round-0 warp**: in round-2 play, `E722 = 0xA356` (the type-70 idx-88 totem's
  `+0x1C/1D`) + `E102` bit 5 → `E701 → 0`, round 0 loaded (screenshot). ✓
- **Type 82 = fire box**: broke on the 0xD2 digit draw (0x87F6) with `+0x1C = 1`
  and captured the two blue "2"/"1" fire boxes at round-1 start. ✓
- **Destruction map** (0x880D) decoded byte-exactly: only `+0x18 < 0x51` spawns
  the orb; `0x52` and the `0x88A2` `R&7` path spawn **fire** (type 0x53), not a
  warp. ✓

## See also

[[M-secrets-and-warps]], [[handler_type72_base_core]] (orb),
[[handler_type70_wide_structure]] (idol), [[level_script_format]] (cmd 8 → E720),
[[stage_stream_ptr_table]] / `resolve_round_from_ptr` (0x9444),
[[round-progression]], [[level_complete_handler]] (0x40DA), [[explode_enemies]].
