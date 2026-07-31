---
id: "0046"
status: done
range: 0x46D9-0x4774,0x4ACE-0x4AE9,0x9433-0x9443
strategy: subsystem_slice
budget_turns: 22
subsystems: [L]
---

# Sprint 0046 — Subsystem L (Ending & Credits): confirm all routines

## Goal

Take subsystem L to fully documented (all `confirmed`). `credits_display` and
`init_credits_stream` were `likely`, and `compare_save_hiscore` (0x4ACE) had no
KB entry. Confirm the two routines live and document + confirm the hi-score save.

## Inputs

- `kb/subsystems/L-ending-and-credits.md`
- `kb/symbols/0x4000-init/credits_display.md`, `kb/symbols/0x9000-scroll/{ending_setup,init_credits_stream}.md`
- `kb/guides/input-state-machine.md` (§ end-credits)
- Source: credits_display 0x46D9, compare_save_hiscore 0x4ACE, init_credits_stream 0x9433.
- Tools: `savestates/game-end.oms` (round-8 boss kill).

## Verification plan

`tools/sprint0046_verify.py` — Phase A `ZanacGame` microexec (compare_save_hiscore,
init_credits_stream); Phase B `ShotSession` on the end savestate (credits_display
entry + screenshot + ESC→title).

## Summary (filled at end)

**All 10 checks passed; subsystem L → fully documented ✓.**

### Confirmed

| Addr | Routine | Evidence |
|------|---------|----------|
| 0x4ACE | `compare_save_hiscore` (new entry) | microexec: score>hs → copy (C=0); score<hs → unchanged (C=1); equal → copy. End-to-end: credits HUD shows TOP==SCORE==2211200 |
| 0x9433 | `init_credits_stream` | microexec HL=0xBBB4 → E701=8 (resolve_round_from_ptr), E704:E705=0xBBB6 (HL+2); HL=0 → RET Z, E701 untouched |
| 0x46D9 | `credits_display` | from `game-end.oms`: 0x46D9 reached, hi-score save (0x46DD) fired on entry, screenshot shows "GAME DESIGN/JANUS/MOO/JEMINI" over round-0 scroll, ESC → title (0x4042) |

### Screenshot

`/tmp/zanac_credits.png` — centred staff roll over the round-0 terrain, HUD
**ROUND 0**, **TOP = SCORE = 2211200** (hi-score promoted on entry), player ship
present (controllable during credits, as documented).

### Source

- `compare_save_hiscore` (0x4ACE) — label renamed from `SUB_ram_4ace`; 2 call-site
  comments (0x4672, 0x46DD) updated. `redisasm verify` byte-identical.

### Files

- New `kb/symbols/0x4900-hud/compare_save_hiscore.md`.
- `credits_display.md` / `init_credits_stream.md` → `confirmed` + live notes.
- `L-ending-and-credits.md` — coverage `done`, gaps cleared, routine added.
- `CLAUDE.md` coverage table L → done ✓.
- `tools/sprint0046_verify.py`.

`zanackb validate` 0 errors. `redisasm verify` byte-identical.
