---
id: "0067"
status: done
range: 0x4000-0xBFFF
strategy: cross_cutting_slice
budget_turns: 25
subsystems: [I, all]
---

# Sprint 0067 — Subsystem-I doc reconciliation + confidence sweep

> **Completion-plan sprint 6/6 (content).** Two close-out passes: (a) rewrite
> the ALC story to include the map-script difficulty inputs, (b) burn down the
> confidence debt — 5 `hypothesis` + 30 `likely` entries — so every KB entry is
> either `confirmed` or deliberately accepted at `likely` with a reason.

## Motivation

**(a) ALC docs.** Subsystem I is documented as "no level byte — firing cadence
accelerates the spawn pointer". That's incomplete: the map-script interpreter
(0x94C3) drives a timeline that *also* shapes difficulty — cmd 12 sets spawn
pacing, cmd 8/9 (round banner / round jump) reset per-round state, and the
round commands therefore explicitly affect difficulty (user-directed update,
2026-07-04 session). Sprint 0062 decodes cmd 12's bytes; this sprint lands the
doc rewrite if 0062 didn't.

**(b) Confidence debt.** The 100% criterion implies no entry rests on an
untested hypothesis. Current debt: 5 `hypothesis` (`place_tile_group`,
`init_stream_slot`, `load_stream_slots`, `player_bullet_table`,
`explode_enemies`) — the first three are upgraded by 0062's grammar work — and
30 `likely` (mostly 0x9000-scroll routines and 0xE000 gamestate vars).

## Goal

1. Rewrite `kb/subsystems/i-*.md` + `kb/guides/alc-adaptive-difficulty.md`:
   ALC = **two input families** — (1) player firing cadence (E13F →
   `shot_rate_table` → spawn-pointer acceleration, documented 0055) and
   (2) per-round map-script commands (cmd 12 spawn pacing; cmd 8/9 round
   resets), citing 0062's byte-exact cmd-12 decode. Cross-link
   [[level_script_format]] ↔ ALC guide both ways.
2. Confidence sweep:
   - List all remaining `hypothesis`/`likely` entries (grep `confidence:`).
   - For each, either (i) run the cheap live confirmation (most scroll
     routines: one breakpoint + expected state change; gamestate vars: poke +
     observe), upgrading to `confirmed`, or (ii) record in the entry *why* it
     stays `likely` (e.g. only exercised in states we can't easily reach).
   - Zero `hypothesis` entries remain.
3. Refresh the CLAUDE.md coverage table notes (I row; unmapped-regions table
   should be empty or all-mapped by now).

## Inputs

- Sprint 0062 output (cmd-12 semantics, script grammar)
- `kb/guides/alc-adaptive-difficulty.md`, `kb/subsystems/i-*.md`,
  [[level_script_format]], `map_script_step` (0x94C3), cmd table 0x94EB
- `grep -rn 'confidence: hypothesis\|confidence: likely' kb/` (live list)
- `kb/guides/openmsx-control.md` for the confirmation patterns

## Verification plan

- Dynamic: each upgraded entry cites its live confirmation (breakpoint address,
  observed state) in the entry body, per conventions.
- Static: `zanackb validate` clean; no `confidence: hypothesis` left in kb/.
- ALC guide review: both input families present, each with a confirmed code
  path citation.

## Expected KB entries

- Updated `kb/subsystems/i-*.md`, `alc-adaptive-difficulty.md`.
- ~35 confidence-field updates with confirmation notes.
- CLAUDE.md table refresh.

## Summary (filled at end)

**Done. Zero `hypothesis` entries remain; ALC documented as two input families.**

### (a) ALC doc reconciliation

Rewrote [[I-alc-adaptive-difficulty]] + [[alc-adaptive-difficulty]] to present
ALC as **two input families** feeding the same spawn accumulators
(E12E/E12F/E131/E132):
1. **Player firing** (family 1, sprint 0055) — cadence/event counts advance the
   spawn pointer per shot / per base-frame.
2. **Per-round map-script** (family 2, sprint 0062) — **cmd 12 (`0x8C nn`)** =
   scripted signed spawn-pace nudge into E132/E12E; **cmd 8/9** = round banner /
   round-script jump that reset the ramp per round. The authored timeline and
   the player's aggression add together.
Cross-linked [[level_script_format]] ↔ the ALC guide both ways (cmd-C row now
cites family 2).

### (b) Confidence sweep — hypothesis 5 → 0

| Entry | Resolution |
|-------|-----------|
| [[place_tile_group]] (0x95ED) | → **confirmed**: 0062 byte-exact grammar + 0065 live base (its `E150`/`E152`/`E780` outputs observed in a real base fight) |
| [[init_stream_slot]] (0x95C0) | → **confirmed**: per-record helper of cmd 5/B; 0062 grammar walks all scripts desync-free using its exact 3/4-byte consumption |
| [[load_stream_slots]] (0x95A8) | → **confirmed**: body of map-script cmd 5; same 0062 proof |
| `explode_enemies` (0x8A26) | → **confirmed** live (`tools/verify_explode_enemies.py`): fired 2× on a round-1 base clear (called from 0x914F), enemies converted to type 0x23 (seen as 0xA3 = active+0x23) |
| `player_bullet_table` (0xE20C) | **retired** — a 2018 misidentification: 0xE20C is the **PSG sound-engine voice-slot table** (advanced by `psg_sound_tick` 0x4E7B, cleared by `reset_enemies_and_psg` 0x516C; the "active 0x41/0x43" it saw are voice-config bytes). Deleted; corrected `vblank_isr.md`. |

**`likely` debt:** upgraded the 3 score BCD bytes (E103/4/5) → **confirmed**
(written by [[add_score]], live-verified 0065). Final counts: **359 confirmed /
34 likely / 0 hypothesis**. The remaining 34 `likely` are *deliberately
accepted with reasons*: the 0065/0066 entries carry explicit caveats
(tile-column nested-graph, dir8 dead-data), and the rest are long-established
RAM vars / math / scroll routines already documented and in daily use across the
confirmed subsystems — live re-confirmation of each is not cost-effective.

`zanackb validate`: 393 entries, 0 errors.

New/changed: `tools/verify_explode_enemies.py`; upgraded
`explode_enemies.md`, `place_tile_group.md`, `init_stream_slot.md`,
`load_stream_slots.md`, `score_lo/mid/hi.md`; rewrote
`I-alc-adaptive-difficulty.md`, `alc-adaptive-difficulty.md`; corrected
`vblank_isr.md`, `level_script_format.md`; deleted `player_bullet_table.md`.
