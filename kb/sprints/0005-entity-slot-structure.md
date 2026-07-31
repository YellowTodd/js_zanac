---
id: "0005"
status: done
range: 0x70B7-0x76FF
strategy: forward_from_caller
budget_turns: 30
---

# Sprint 0005 — Entity slot structure

## Goal
Decode the 32-byte entity slot layout at 0xE300, map the entity-type jump table at
0x70B7, and identify every data region referenced during the entity dispatch cycle.
Context note: `kb/features/zanac-sprite-names.md` provides semantic names for
sprite patterns 0–63; a "shadow" entry is a secondary sprite for multi-color
overlay, not a separate entity.

## Inputs
- `kb/symbols/0x4000-init/entity_dispatch.md` — jump table address 0x70B7
- `kb/data/entity_table.md` — array base and slot width
- `kb/symbols/0x4000-init/vblank_isr.md` — OUTI DMA from 0xE000
- `kb/features/zanac-sprite-names.md` — pattern numbers to entity names
- `source/zanac.asm` lines 78–82 (entity slot type byte init)
- `source/zanac.asm` lines 264–290 (player entity struct init at 0xE100)
- `source/zanac.asm` lines 1344–1418 (player bullet table at 0xE20C)
- `source/zanac.asm` lines 2413–2418 (entity type jump table at 0x70B7)
- `source/zanac.asm` lines 2495–2505 (type-1 power-chip handler: init + motion)

## Verification plan
- Static: confirm slot[1]/slot[2] map to Y/X by cross-checking clamping bounds
  (Y ∈ [30,184], X ∈ [40,200]) against on-screen sprite coordinates.
- Dynamic: openMSX — set BP at entity_dispatch entry; read 0xE300 after a few
  frames of gameplay; decode slot[0] type, slot[1] Y, slot[2] X.

## Summary

**Entity slot structure (0x20 bytes):**
Fully decoded motion fields from type-1 handler code (lines 2495–2505); slot is a
fixed-point position + velocity record with a type/flag byte at offset 0.
Positions clamped to Y ∈ [30,184], X ∈ [40,200] each frame.

**Entity type jump table (0x70B7):**
26 16-bit LE entries (types 0–25; type 0 never dispatched). Type 1 = power-chip
handler confirmed at 0x75D5. Several types share handlers (4–6, 12–15, 22–23,
24–25). Types 20–21 point into labeled 0x8000+ code (0x8635, 0x8668).

**New data regions found:**
- Player state flags + sprite entry at 0xE200–0xE20B.
- Player bullet table at 0xE20C: 5 × 27-byte bullet slots (cleared by `sub_516c`).

**Still uncertain:**
- Sprite shadow buffer format: handler writes (pattern, Y, X) — whether shadow
  layout is SAT-compatible or reorganized by the ISR needs dynamic confirmation.
- Slot offsets 3–5 and 12–27 role (partially initialized in type-1 handler).
- Type IDs 2–26 to sprite-name mapping (not yet decoded beyond type 1).
- Player bullet slot struct (27 bytes) internal layout.

**Next sprint candidates:**
- **0006 — Jump table survey**: read handlers for types 2–6 (comet, target, etc.),
  confirm sprite pattern written per handler, map type → sprite name.
- **0007 — Player bullet struct**: decode sub_5199 + sub_516c to map 27-byte
  bullet slot fields (velocity, pattern, lifetime).
- **0008 — 0x9A79 (enemy-update ISR call)**: decode the routine called every
  VBLANK; expect sprite coordinate update + collision tests.
