---
id: "0057"
status: done
range: 0x5234-0x5A11
strategy: data_table
budget_turns: 20
subsystems: [O]
---

# Sprint 0057 — Subsystem O sound-event catalogue (closing slice)

> **Subsystem slice:** [[O-sound-system]] — the closing slice. Sprint 0020 built
> the engine architecture and 0028 decoded the track command format; this sprint
> catalogues **all 27 events** (music vs SFX + purpose) and upgrades
> `reset_enemies_and_psg`.

## Goal

1. Identify every event 1–27 in the table at 0x5234: voice count / channels
   (structure) and its in-game purpose (from `play_sound_event` 0x5189 call
   sites).
2. Upgrade `reset_enemies_and_psg` (0x516C) from `hypothesis`.
3. Resolve the sprint-0028 outstanding question "per-event purpose of events
   1–2, 5–27".

## Method

- **Structure:** decoded each event header from ROM (N voices; per voice
  descriptor/cfg/amp/curve/tempo/channel/stream ptr) and its byte size (distance
  to the next event pointer). `tools/decode_track.py` + a header scan.
- **Purpose:** static scan of all `CALL 0x5189` sites and the `LD A,n` (or
  computed A) feeding each, mapped to the enclosing subsystem.
- **Chaining:** scanned track data 0x52E2–0x5A11 for the `0x87 nn` PLAY_EVENT
  command (a track spawning another).

## Summary (filled at end)

### Structure split (confirmed from headers)

- **Multi-voice music/jingles** (3 voices unless noted): 1, 2 (2v), 3, 4, 5 (2v),
  7, 8 (2v), 9 (2v), 10, 11, 12, 25, 26, 27.
- **Single-voice SFX** (all channel C / ch2 except 24 = ch1, mostly noise mode):
  6, 13, 14, 15, 16, 17, 18, 19, 20, 21, 22, 23, 24.

### Trigger map (from call sites + live confirmation)

- **Round-start BGM** (0x405D–0x4065): plays **event 7** when `round & 7 ≠ 0`,
  else **event 2** (rounds ≡0 mod 8). Event 7 (intro) immediately **chains to
  event 1** (long 239-byte main theme). Live-confirmed: at gameplay start event 7
  fired (caller ret 0x4068), then event 1 fired from the sound engine itself
  (`advance_track_stream` ret 0x4F51) via the `0x87 01` PLAY_EVENT at 0x565D.
- **Shot fire SFX** (0x7234): plays `event = 3 + ((0xE10F) >> 2)`, transpose from
  0xE10F — the shooting sound scales with the shot-state byte 0xE10F (loaded with
  0xE10D/E from a parameter block at 0x778B). Live: event 13 fired repeatedly
  while shooting. **(Corrected the mid-sprint "play_bgm/stage-BGM" hypothesis —
  this is the shot SFX, not BGM.)**
- **Track chaining** (`0x87` PLAY_EVENT): event 7 → event 1 (@0x565D) and
  event 12 → event 5 (@0x5804).
- **Title / attract**: event 3 @0x5A16 (title_intro — also the round-base BGM);
  event 4 @0x467B (game-over / attract).
- **New-game init** (0x40xx): event 2 @0x4065, event 11 @0x40EA, event 10 @0x4133.
- **State jingles** gated on `0xE102` bit2: event 9 @0x4A20, event 8 @0x4A61
  (also 8 @0x8763).
- **Round/boss transition**: event 25 @0x9044 (conditional), event 12 @0x924B,
  events 26/27 @0x917A (`C=0x1A`/`0x1B`, round-clear fanfares).
- **SFX by firer**: weapon/fire (F) → 6 @0x7260, 24 @0x74C1/0x74E2, 19 @0x7516;
  player (F) → 23 @0x78C1, 20 @0x7911; enemies (G) → 21 @0x8025/0x8209,
  16 @0x86C0, 17 @0x8495/0x8B87, 19 @0x89FF, 20 @0x8438 (base);
  **explosion = event 18** @0x8879/0x8E1F (base damage/death).

Full per-event table added to `kb/guides/sound-engine.md` (replaces the old
3-row "Known events").

### reset_enemies_and_psg (0x516C) → confirmed

Decoded fully: clears slot[0] (active flag) of all 5 voice slots then
`WRTPSG(R7, 0xBF)` — a pure **stop-all-sound**. The "enemies" in the name is a
legacy misnomer (it touches only PSG); callers reset enemy state separately.
Confidence hypothesis → confirmed; added inputs/outputs/clobbers/called_by.

### Live confirmation (`tools/sprint0057_verify.py`)

Breakpoint on `play_sound_event` (0x5189), logging event # + caller:
- Title: `{3 5A19}` → event 3 = title music ✓.
- Gameplay start + shooting: `{7 4068}` (round-start BGM intro) → `{1 4F51}`
  (event 1 fired *by the sound engine's PLAY_EVENT handler* — confirms the 7→1
  chain) → `{13 7237}`×4 (shot SFX while firing) → `{16 86C3} {17 8498}` (enemy
  SFX). Every observed event matched the static call-site map.

### Deliverables

- `kb/guides/sound-engine.md`: full 27-event catalogue (structure + purpose +
  chaining), round-start BGM (7/2→1), shot-SFX selector (0x7234 / 0xE10F),
  PLAY_EVENT chaining; resolved the 0028 outstanding question.
- `reset_enemies_and_psg.md` upgraded to confirmed.
- `O-sound-system.md` → done; CLAUDE.md coverage + DB tracker updated.
- `tools/sprint0057_verify.py` (live event logger).
- `zanackb validate`: 0 errors.

### Left open (data, not structure)

- Byte-exact "score" of every track (only event 3 fully transcribed, in 0028) —
  this is content, not undocumented structure.
- Exact note→period index math in the 0xF200 frequency table (stride quirk),
  and pitch-slide / vol-env fine details — engine internals flagged in 0028.
