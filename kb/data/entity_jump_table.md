---
address: 0x70B9
end: 0x7166
kind: data
name: entity_jump_table
confidence: confirmed
sprint: "0012"
tags: [entity, dispatch]
---

# entity_jump_table

## Summary

Array of 16-bit LE handler addresses indexed by entity type × 2. Used by
`entity_dispatch` (0x445F): for slot type T, jumps to `*(0x70B7 + T×2)`.
Type 0 is never dispatched (inactive slot). Physical table starts at 0x70B9 (type 1, first entry that is ever dispatched).
`entity_dispatch` uses virtual base `0x70B7` so the formula `0x70B7 + type×2`
lands on the correct entry; 0x70B7–0x70B8 are the RLE tail of `gfx_sprite_patterns`.
Table extends from 0x70B9 to
at least 0x7165 (type 87), covering ~89 valid types. Types 90+ point into
the BIOS area (invalid/unused).

All confirmed by direct openMSX memory read (sprint 0012).

## Full table

| Type | Handler | Role | Confidence |
|------|---------|------|------------|
| 0 | (0x00AA) | **never dispatched** — virtual slot; 0x70B7–0x70B8 are RLE tail of sprite data | — |
| 1 | 0x75D5 | **player ship** | confirmed |
| 2 | 0x7221 | player shot (reads shot SAT_NAME from 0xE10F, vy from 0xE10E) | likely |
| 3 | 0x7253 | fire weapon 0 projectile — large_circle sprite, cycles all 16 colors to signal player origin | confirmed |
| 4 | 0x7826 | **box enemy** — SAT_NAME used as countdown (→0 triggers spawn_col_marker + real pattern 0xD4); vy_frac=0xC0 slow descent; complement 0xD8 (pat 54); +0x19=5 on activation (shared 4–6) | confirmed |
| 5 | 0x7826 | (same — shorter countdown variant observed) | confirmed |
| 6 | 0x7826 | (same — longer countdown variant; +0x1D varies with type) | confirmed |
| 7 | 0x791D | **umber enemy** — pattern 0xDC (pat 55), color 0x8F, vy=3 downward, bflags=0x09 Y+Yhom, y_acc=16, complement 0xE4; Y-homes toward top → exits screen quickly; when fully stopped spawns burst of 7 type-38 entities; probe +0x18=7 confirms init+entity_post executed | likely |
| 8 | 0x79BE | umber variant — same init as type 7; color patched to 0x8B; when stopped spawns 2 type-41 entities; probe +0x18=8 confirms init executed | likely |
| 9 | 0x79FB | umber variant — same init as type 7; pattern 0xE0 (pat 56) color 0x83 cyan; countdown timer (+0x1D=8) periodically spawns type-20; probe +0x18=9 confirms init executed | likely |
| 10 | 0x7A2A | **duster** — pattern 0x58 (pat 22), color 0x89, Y+X+X-homing (0x13), vy=3; R-bit sets target_x direction; complement 0x5C (duster_compl) | confirmed |
| 11 | 0x7AD4 | **base projectile spawner** — reads 0xE130, changes own type to 69 | confirmed |
| 12 | 0x7B07 | **teruzo** — pattern 0x60 (pat 24), color 0x8A, bflags=0x03 (Y+X motion), vy=-2 (upward), vx=+1 (rightward); lower-screen spawn Y=112 | confirmed |
| 13 | 0x7B07 | teruzo — same as type 12 but vx=-2 (leftward) | confirmed |
| 14 | 0x7B07 | teruzo — upper-screen spawn Y=32, color 0x89, vx=+1 (right edge X=208) | confirmed |
| 15 | 0x7B07 | teruzo — upper-screen spawn Y=32, color 0x89, vx=-1 (left edge X=16) | confirmed |
| 16 | 0x7BEB | **luster** — pattern 0x78 (pat 30), color 0x8E; bflags=0x01 Y-motion only; vy=2 straight fall; spawns col-marker; +0x1E=0xC0 | confirmed |
| 17 | 0x7C8A | **luster homing** — pattern 0x78 (pat 30), color 0x8E; bflags=0x13 Y+X+X-hom; vy=2 vx=+3; tgt_x=~176 x_accel=64; spawns col-marker; +0x1E=0xE0 | confirmed |
| 18 | 0x7CB3 | **luster left** — pattern 0x74 (pat 29), color 0x8B (light-red); bflags=0x13 Y+X+X-hom; vy=2 vx=−1; tgt_x=0xFF x_accel=14; spawns col-marker; col_wid=22 | confirmed |
| 19 | 0x74A4 | changes own type to 0x83 (→ type3 running); reads 0xE14B | hypothesis |
| 20 | 0x8668 | **lead homing** — pattern 0x1C (pat 7), color 0x8F; bflags=0x0B Y+X+Yhom; tgt_y=0xFF (homes to bottom off-screen); y_acc=12; random X spawn; spawned by type-9 timer | confirmed |
| 21 | 0x8635 | **light_bar** — pattern 0x18 (pat 6), color R-random 0x84–0x85; bflags=0x03 Y+X; vx=+2 rightward | confirmed |
| 22 | 0x7D0F | **veybar** — pattern 0x84 (pat 33), color 0x83 cyan; bflags=0x09 (Y-motion+Y-homing); vy=4; R-bit sets spawn side (X=200 vx=−1 or X=40 vx=+1); complement 0x98 (pat 38); +0x1D=80 countdown (shared 22–23) | likely |
| 23 | 0x7D0F | veybar — (same as type 22, R-bit independently randomized per spawn) | likely |
| 24 | 0x7DB4 | **veybar fast** — pattern 0x84 (pat 33), color 0x89 light-blue; bflags=0x1B (Y+X motion + Y-homing + X-homing); vy=4; R-bit sets spawn side (X=184 vx=−3 or X=56 vx=+3); +0x1D=88 (shared 24–25) | likely |
| 25 | 0x7DB4 | veybar fast — (same as type 24) | likely |
| 26 | 0x7DE2 | **edge-swooper A** — 4-frame anim table 0x7E68 (pats 43–46, color 0x8E); bflags=0x0F Y+X+anim+Yhom; vy≈1.8 downward; spawns right X≈180; complement = sat_name+0x10; +0x1D=0x25 from HL init; probe confirms pat 44 mid-anim | confirmed |
| 27 | 0x7DF3 | edge-swooper A — same as type 26 from left X≈59; +0x1D=0x14 from HL init; probe confirmed | confirmed |
| 28 | 0x7E78 | **edge-swooper B** — anim table 0x7E70 (pats 43–46, color 0x87 dark-green); spawns right; +0x1E countdown=4 | hypothesis |
| 29 | 0x7E86 | edge-swooper B — same as type 28 from left | hypothesis |
| 30 | 0x7E9C | **ground swooper** — pattern 0xEC (pat 59), color 0x8F; bflags=0x01 Y-only; vy≈1.5 (vy=1 vy_frac=0x80); spawns col-marker; shared 30/32 | confirmed |
| 31 | 0x7F84 | **stealth tracker** — pattern 51 (stealth), tracks player Y then X; init spawns stealth_compl col-marker; random X from table 0x807C | confirmed |
| 32 | 0x7E9C | ground swooper — same as type 30 | confirmed |
| 33 | 0x7F84 | (same as 31) | confirmed |
| 34 | 0x7F99 | ground entity — same init as types 31/33 (stealth sprite, col-marker); running code at 0x8012 (no player Y tracking) | likely |
| 35 | 0x8446 | **enemy projectile** — sprite chosen from 0xE141 counter (lead/circle/plane range); NOT base-eye (corrected sprint 0013) | confirmed |
| 36 | 0x8296 | **flashing entity** — pattern 0x34 (pat 13), color 0x8F white; bflags=0x01 Y-motion; vy_frac=0x80 very slow descent; running code XORs sat_col with 0x0E (color flicker); +0x19=0x10; spawns near top Y≈13 | confirmed |
| 37 | 0x84DD | **enemy lead bullet** — pattern 0x1C (pat 7), color 0x8F; bflags=0x03 (Y+X motion); vy=−2 (upward toward player) | confirmed |
| 38 | 0x8501 | **burst fragment** — pattern 0x1C (pat 7), color 0x8F; bflags=0x03 Y+X; vx≈1.5 rightward; spawned in groups of 7 by type-7 umber when stopped | confirmed |
| 39 | 0x8525 | **ground column marker** — countdown at +0x18, despawns via `entity_clear` | confirmed |
| 40 | 0x852C | **instant despawn** — handler is entity_clear; slot zeroed immediately on first dispatch | confirmed |
| 41 | 0x852F | **pair fragment** — pattern 0x1C (pat 7), color 0x8F; bflags=0x03; vx=+3 + Y-homing y_acc=1; spawned in pairs by type-8 umber when stopped | confirmed |
| 42 | 0x85CC | **proto-bullet** — init converts self to type 37 (lead bullet); sets pattern 7 + bflags=0x03; transient init-converter type | confirmed |
| 43 | 0x85D6 | **proto-fragment** — init converts self to type 38 (burst fragment); sets pattern 7 + bflags=0x03; transient init-converter type | confirmed |
| 44 | 0x82D0 | **main ground structure** — places tile 0x44, calls `spawn_col_marker` | confirmed |
| 45 | 0x85EE | **light_bar variant** — pattern 0x18 (pat 6), color 0x8F white; bflags=0x03 Y+X motion; vx=+1; +0x19=3 | confirmed |
| 46–55 | 0x8094 | **ground-structure gun entities** — SAT_NAME 0x48 (pat 18, plane), bflags=0x01 Y-only, vy≈1.313 (vy=1 vy_frac=0x50); X randomised (0x30 left / 0xC0 right via R register); 5-entry subtable at 0x8189 (4 bytes each, pairs share one entry); pair behaviours: 46/47 straight→type-38, 48/49 Y-track→type-21, 50/51 oscillate→type-38, 52/53 straight→type-21, 54/55 oscillate→type-21; parent body addr at +0x1B/+0x1C; fire sub at 0x816D spawns child via 0x8DDB | confirmed |
| 56 | 0x819D | **sig_single (falling pickup/missile)** — pattern 0x70 (pat 28), color alternates 0x8F↔0x86 (XOR 0x09 each frame); bflags=0x03 Y+X; vy≈2.5 downward; +0x1F=0x20 | confirmed |
| 57 | 0x81D1 | **paired descender A** — pattern 0x6C (pat 27), color 0x8F; bflags=0x03 Y+X; vy≈2.5 (vy=2 vy_frac=0x80); spawns col-marker; +0x1F=7 | confirmed |
| 58 | 0x8247 | **paired descender B** — pattern 0x68 (pat 26), color 0x8F; bflags=0x03 Y+X; vy≈2.5; spawns col-marker; +0x1E=0xE4 +0x1F=7 | confirmed |
| 59 | 0x8269 | **sideways entity** — pattern 0x70 (pat 28), color 0x8F; bflags=0x03; vx≈2.5 (vx=2 vx_frac=0x80); no child; +0x1F=0x20 | confirmed |
| 60 | 0x869E | **player death explosion** — 11-frame expanding/contracting animation; bit2-only +0x0C; table at 0x86F3; spawned in slot 0 on player death | confirmed |
| 61 | 0x8302 | **large descender** — pattern 0xF8 (pat 62), color 0x83 cyan; bflags=0x01 Y-only; vy=2; spawns col-marker; +0x1E=32; col_wid=1 | confirmed |
| 62 | 0x8709 | **invisible upward** — pattern 0x00 (invisible), color 0x87; bflags=0x01 Y-motion; vy=−1 (moving up); no child — likely a non-visual trigger entity | confirmed |
| 63 | 0x78AF | **power chip** (item pickup) — floats; on player contact raises `shot_level` (E10B) by 1, **cap 5** (0x78DB `CP 6` refuses the increment, matching [[shot_power_table]]'s 6 entries); maxed → bonus counter E148, and **every 5th** maxed chip (E14F) restarts the current fire. Dropped by a type-6 box. ([[handler_type63_power_chip]]) | confirmed |
| 64 | 0x8279 | **proto-structure** — init converts self to type 44 (main ground structure); sets pattern 0x40 (pat 16, plane), color 0x83 cyan; spawns col-marker at 0xE3A0; transient init-converter | confirmed |
| 65–66 | 0x7F99 | same as type 34 (stealth sprite, no player-Y tracking) — type-65 active (0xC1) triggers color/counter overrides in init | likely |
| 67 | 0x839F | **med_circle entity** — pattern 0x20 (pat 8, med_circle), color 0x86 (EC+6 dark); bflags=0x03 Y+X; +0x19=5; child_ptr field used for non-standard purpose (0x1E5E — not a valid entity slot) | confirmed |
| 68 | 0x77A1 | **proto-box** — init converts self to type 4 (box enemy); identical box setup (pattern 0xD4, vy_frac=0xC0, +0x19=5); spawns col-marker; transient init-converter | confirmed |
| 69 | 0x7A67 | **base projectile (running)** — spawned by type 11 | confirmed |
| 70–71 | 0x87AB | wide ground **totems**. **Type 71 = "smiling totem"** (specific-round warp dests from +0x1C/1D); **type 70 = plain totem** (round-0 / normal dests, incl. the round-2 "invisible totem" → R0). Both spawn a type-72 orb when +0x18<0x51 (sprint 0060/0061, [[idol-warp-orbs]]) | confirmed |
| 72 | 0x8983 | **warp/power ORB** (spawned by a destroyed idol) — pattern 0x24 (lg_circle), color 0x8A, drifts up (≈−0.03 px/f); +0x1E=4 yellow→black timer: yellow touch = kill-all, black touch = **warp** to +0x1C/1D ([[idol-warp-orbs]], [[handler_type72_base_core]]) | confirmed |
| 73–79 | 0x8A5A | **base-gated group** — init blocked unless 0xE150 bit1=1; type 73 probe: pattern 0x20 (pat 8, med_circle), transparent (sat_col=0x00), bflags=0x00, +0x19=40; velocity/homing from live game-state; 7 types at handler 0x8A5A | confirmed |
| 80 | 0x8E14 | **base damage handler** — calls `base_encounter_ctrl` DECREMENT | confirmed |
| 81–82 | 0x87AB | wide ground structure (same as 70/87). **Type 82 = fire-powerup box** (blue 4×4, digit = fire# via 0xD2 draw at 0x87E2; +0x18=0x52 → spawns type-83 fire upgrade). NOT a warp totem (sprint 0061, screenshot-confirmed) | confirmed |
| 83 | 0x8E3A | **black shadow entity** — pattern 0x04 (pat 1), color 0x81 (black/complement); bflags=0x01 Y-only; vy=0xFF vy_frac=0xE0 (≈−0.12 px/frame upward); type_flags set to 0xD3 (=0x80|83) on init; +0x1B used as table index (value 0x1A=26 at probe) | confirmed |
| 84–86 | 0x8EB7 | wide structure variant — calls `sub_8F25`, joins 0x87AB at 0x87C3 | likely |
| 87–89 | 0x87AB | wide ground structure (same group) | confirmed |

## Shared-handler groups (same ROM code, different init state)

| Handler | Types | Likely role |
|---------|-------|-------------|
| 0x7826 | 4–6 | box enemies (countdown spawn, 3 countdown variants) |
| 0x791D→0x7954 | 7–8 | umber enemies (init shared; type-8 patches color 0x8B at 0x79C7; running shared) |
| 0x7B07 | 12–15 | teruzo (4 spawn positions: lower-R, lower-L, upper-R, upper-L) |
| 0x7D0F | 22–23 | veybar (Y-homing; R-bit spawn side) |
| 0x7DB4 | 24–25 | veybar fast (Y+X homing; R-bit spawn side) |
| 0x7DE2→0x7DFF→0x7E3F | 26–27 | edge-swooper A (anim table 0x7E68) |
| 0x7E78→0x7E92→0x7E06→0x7E3F | 28–29 | edge-swooper B (anim table 0x7E70) |
| 0x7E9C | 30, 32 | ground enemies with child marker |
| 0x7F84 | 31, 33 | player-tracking entities |
| 0x7F99 | 34, 65, 66 | ground entities |
| 0x8094 | 46–55 | ground-structure gun entities (5-pair subtable; spawns types 38 / 21) |
| 0x8A5A | 73–79 | base-gated entities (7 variants) |
| 0x87AB | 70–71, 81–82, 87–89 | wide ground structures |
| 0x8EB7 | 84–86 | wide structure variants |

## Key entity dispatch helper routines

| Address | Name | Role |
|---------|------|------|
| 0x48D0 | `entity_clear` | Zeroes the 32-byte entity slot (type→0 = despawn) |
| 0x71DA | `spawn_col_marker` | Allocates a type-39 slot, links to parent via +0x1B/1C |
| 0x71C5 | `random_x_pos` | Computes random X position via 0x43C0, stores to +0x02 |
| 0x4496 | `find_free_slot` | Scans slots 5–25 (0xE3A0, step 0x20, 21 entries) for type_flags==0; returns HL=slot or SCF if full |
| 0x8DDB | `spawn_entity` | Stores entity type A into the slot found by `find_free_slot`; used to spawn child enemies mid-game |
| 0x4898 | `entity_update` | Dispatches IX+0x0C behavior flags (motion/shoot/animate) |
| 0x44BA | `entity_post` | Common epilogue: sprite push + collision check |
| 0x8F25 | `wide_struct_init` | Gate: waits for scroll_flags bit 1 before init; scrolls Y |
