---
letter: M
title: Secrets & Warps
coverage: done
status: done
---

# M — Secrets & Warps

## Role

Non-standard entry paths into the game's rounds:

1. the title-screen **ESC-continue** (resume the last round instead of
   restarting at round 1), and the **round 0** "secret" stage it can reach;
2. the in-game **warp orbs** — shoot a ground **idol**, let the orb it releases
   turn black, touch it, and get teleported to another round (even an earlier
   one).

M owns no code of its own; it documents how routines in [[J-title-screen]],
[[K-game-flow-state-machine]], [[G-enemy-and-spawn-system]] and
[[E-level-data-and-decompression]] combine to expose these paths. Sprint 0058
confirmed the title/round-0 picture; sprint 0059 reverse-engineered and
live-confirmed the idol/orb/warp mechanic (full details + per-round destination
catalogue in **[[idol-warp-orbs]]**).

## The two facts that make "secrets" possible

Everything here follows from two design details already documented elsewhere:

1. **The round selector `E701` is not reset unconditionally at game start.**
   `title_screen_init` (0x424C) resets `E701 = 1` **only when ESC is *not* held**;
   with ESC held it keeps whatever value `E701` had (`check_esc_key` 0x43D2,
   [[J-title-screen]]). The start table is indexed by `8 − E701`
   ([[stage_stream_ptr_table]] 0x945C), so any `E701` in 0..8 selects a valid
   stream — including **`E701 = 0`** (index 8 → stream **0xA65C**).

2. **`E701 = 0` is a real, playable stage, not just the ending.** The round-0
   stream 0xA65C is a full scrolling level with its own terrain; the game's
   **ending** is a later segment of that same stream (0xA6F4) dressed with the
   ZANAC-logo tiles and the credits flag (see [[ending_setup]]). So "round 0"
   read as a normal round *is* the secret area.

## The ESC-continue (the only real in-game secret input)

| ESC at title | `E701` | Starts at |
|--------------|--------|-----------|
| not held (normal) | reset to 1 | round 1 |
| **held while starting** | **unchanged** | **last round reached** |

On a **cold boot** `E701` is already 1 ([[cold_start]]), so ESC+SPACE and plain
SPACE are identical. Continue only does something once `E701` has been advanced
during the current power cycle. Reaching **round 0** by continue therefore
requires `E701` to have been left at 0 by a prior life — which in unmodified play
happens only at the end sequence (round 8 → 0, below). See
[[keyboard-input]] and `scripts/warp.tcl`.

## How `E701` reaches 0 (round-advance mechanism)

The round counter advances by *resolving the next stream pointer* in `E722`, not
by `INC` ([[round-progression]]). `E722` is written from three sites:

| Writer | Addr | When | Next stream |
|--------|------|------|-------------|
| scroll round-script jump | 0x91F4 | map-script cmd 9 ([[D-scroll-and-tile-rendering]]) | hardcoded (e.g. 0xB7A5 = round 8) |
| **warp orb touched black** | 0x8A0B | [[handler_type72_base_core]] (the orb) touched with `+0x1E`==0 | its own `+0x1C/1D` = warp destination (from the round's idol table) |
| final-boss / ending | 0x92B2 | end of round 8 ([[ending_setup]]) | 0xA6F4 → resolves to **round 0** |

`level_complete_handler` (0x40DA) then runs `resolve_round_from_ptr` (0x9444),
which maps the eight round pointers to 1..8 and **anything below round 1 to 0**,
and stores the result in `E701`. Two unmodified paths reach `E701 = 0`: the
round-8 → ending transition, and a **warp orb whose destination resolves below
round 1** — round 2's **type-70 "invisible totem"** carries `+0x1C/1D = 0xA356`
(< 0xA751 → round 0), the in-game route to the secret stage (live-confirmed 0061).
A complete totem census of all 9 rounds found this to be the **unique** in-game
round-0 gateway ([[idol-warp-orbs]] §search). There is **no second loop** and no
lap counter.

## In-game warp orbs (the real "idol" mechanic)

The stub's "warp orb released by an idol base" was **correct** — my earlier
(0058) dismissal of it as folklore was wrong. Shooting a ground **idol**
([[handler_type70_wide_structure]]) releases a floating **orb**
([[handler_type72_base_core]], type 72); a **yellow** orb kills all enemies, a
**black** orb (its `+0x1E` timer spent) **warps** the player to the round encoded
in `+0x1C/1D` — copied from the per-round **idol table at 0xE720** (set by
map-script cmd 8). Full state machine, sub-type conditions, and the **per-round
warp-destination catalogue** are in **[[idol-warp-orbs]]**. Highlights: round
**2 → 1** and round **5 → 4** are genuine warps to *earlier* rounds; **round 7
loops** (totems offer only R7-self or R8) until you beat the final base or take an
R8 orb. **Round 0** is reached from a round-2 **type-70 "invisible totem"**
(idx 88, dest 0xA356 → R0; live-confirmed 0061). Warp totems are the black-and-
white **"smiling totem"** = entity **type 71**; **type 70** = plain totem. (The
blue digit boxes are **type-82 fire dispensers**, not totems; the `LD A,R & 7`
sub-type is a **random fire type**, not a random warp.) Live-confirmed 0059–0061.

## No hidden key combos

All keyboard reads in the ROM are catalogued: title start-keys and ESC
(0x4366/0x438B/0x4396/0x43D4) and the pause STOP/SELECT reads
(0x4DAA `pause_handler`, 0x4E1B `pause_frame_tick`). There is **no** gameplay-time
`SNSMAT` read that could decode a cheat combo. The stub's "key combos / forced
round unknown" gap is closed: the only secret input is ESC-continue.

## `scripts/warp.tcl` (developer tool, not an in-game secret)

Breaks at `LAB_425a` (0x425A) — the point *after* the ESC test where `E701` is
about to be read as the table index — and overwrites `E701` with any round 0..8.
It exploits fact (1) directly and is the practical way to visit any round,
including 0. Not reachable without the debugger.

## Live confirmation (sprint 0058)

`tools/sprint0058_verify.py`:

- ROM: `stage_stream_ptr_table[8]` (E701=0) = **0xA65C** ✓.
- Warp: one-shot bp at 0x425A forcing `E701 = 0`, then SPACE to start →
  `E701` stayed **0**, gameplay ran (`E102`/`E700` non-zero). Screenshot shows a
  full playable stage — red terrain with blue vertical stripes, a "**ROUND 0**"
  banner, the ship, a base block, and the HUD reading **ROUND 0 / LEVEL 0**. This
  is visually distinct from the black ZANAC-logo ending terrain, confirming round
  0 is a genuine stage whose tail segment is reused for the ending.

## Gaps / open questions

- **Per-round idol census — done (0060):** all specific-round warp idols are
  entity **type 71**; destinations catalogued in [[idol-warp-orbs]]. Still open:
  the byte-exact **placement-stream** format (the greeble records that assign each
  idol's `+0x03` index / position) — a full static decode was superseded by the
  live census; the record format itself remains only partially modelled.
- **`LD A,R & 7` sub-type — resolved (0061):** it is a **random fire type**
  (feeds the type-83 fire branch), *not* a random warp. There is no random-warp
  mechanism.
- Whether the "forward" totem pointers (R1→2, R2→3, R5→6, R7→8) double as the
  normal end-of-round advance or are additional warp options.

## Related

[[idol-warp-orbs]] (warp-orb mechanic + per-round catalogue),
[[handler_type72_base_core]] (orb), [[handler_type70_wide_structure]] (idol),
[[J-title-screen]] (`check_esc_key`, `title_screen_init`),
[[K-game-flow-state-machine]] / [[round-progression]] (`E701`/`E722`,
`resolve_round_from_ptr`, `level_complete_handler`),
[[E-level-data-and-decompression]] ([[stage_stream_ptr_table]], round-0 stream
0xA65C), [[ending_setup]] (round-0 tail = ending), [[keyboard-input]],
`scripts/warp.tcl`.

## Sprints

Done: 0061 (destruction sub-type map: orb vs fire; type-82 = fire box; round-0
"invisible totem" 0xA356 live-confirmed; random-fire correction); 0060 (per-round
totem census — warp totems = type 71 "smiling", screenshot-confirmed; round 7
loops); 0059 (idol/orb/warp mechanic reverse-engineered + live-confirmed,
type-72 correction); 0058
(title/round-0: live warp confirm, round-0 = playable stage, key-combo gap
closed). Earlier context: 0027/0032 (input), 0041 (`check_esc_key`),
0045 (round progression), 0033 (ending stream).
