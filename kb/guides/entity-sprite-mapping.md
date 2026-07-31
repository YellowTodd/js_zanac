# Entity type → sprite pattern mapping

Compiled from live capture (20 frames at `entity_dispatch`, sprint 0013) and
static handler disassembly (sprints 0012, 0013). Confidence per row.

## Pattern index formula

`pattern_idx = SAT_NAME_byte >> 2`  (TMS9918A 16×16 sprite mode, lower 2 bits ignored).

## Sprite complement definition

A **complement sprite** (`_compl`, formerly called "shadow sprite") is a second
SAT entry drawn at the same position as the primary sprite, using color 0x81
(black, EC+1 = nearly transparent dark tint). This gives a two-tone effect,
working around the MSX1 limit of one color per sprite.

## Teruzo rows corrected (2026-07-30)

Rows 12-15 previously gave each type a fixed spawn corner and a fixed velocity
("Y=112 X=208, vy=-2 vx=+1 rightward"). Both parts were wrong, and provably so:
X=208 with vx=+1 crosses `entity_update`'s X despawn bound (209) on the first
step, so that reading despawns the enemy immediately.

The handler (0x7B07) masks the type's low bit away (`AND 0xFE` at 0x7B13) and
adds `R & 1`, so **the corner is random, not per-type**, and there is no fixed
velocity at all: each block in [[teruzo_motion_tables]] is `[Y][X][colour]`
followed by a 16-direction script, one step applied every 8 frames through
[[set_velocity_from_dir]] at speed 4 (bit 7 = hold forever). That entry -
written in sprint 0049 - had the correct model all along; these rows were never
reconciled with it.

## Column-marker / complement-sprite duality

When an entity calls `spawn_col_marker` (0x71DA), the returned HL points to the
new slot's +0x03 (pattern byte). The caller immediately writes the **complement
sprite pattern** there. The parent's running code then repositions the marker
slot's Y/X to match (via IY = child slot), rendering a complement sprite that
follows the parent. The complement slot's type byte is 0x27 (type 39);
`check_col_clear` reads this to block future placements in the same column.

### The three shared helpers, decoded (2026-07-30)

These are called by many type handlers (type 44 at 0x82D0 uses all three), so
they were worth writing out once.

**`spawn_col_marker` (0x71DA)** — allocate the child and hand back its pattern
byte:

```
71DB  CALL alloc_entity_slot        ; HL = free slot, carry if none
71DE  JR C,71F1
71E0  (IX+1B)=L (IX+1C)=H           ; parent links the child
71E6  LD (HL),0x27                  ; child type = 39
71E8  HL += 4; LD (HL),0x81         ; child sat_colour = 0x81
71EE  DEC HL                        ; -> child +0x03, returned to the caller
71F1  POP DE / POP BC / JP entity_clear   ; no slot: the *parent* is killed
```

Note the failure path pops an extra level and clears the parent — an entity that
cannot get its complement slot does not spawn at all.

**`random_x_pos` (0x71C5)** — pick the spawn column:

```
71C5  CALL prng_next
71C8  A = H & 0x7F
71CC  A += L & 0x1F
71D0  A += 0x28
71D2  (IX+0x02) = A                 ; X in [0x28, 0xC6]
71D5  (IX+0x01) = 0x00              ; Y = 0
```

The X range matches the player's own clamp (0x28–0xC8). Y is set to **0**, which
`sprite_shadow_push` treats as "no sprite", so the entity is invisible on its
first frame.

**0x71F6** — push the complement sprite. It writes a *second* SAT record at the
parent's position, taking the pattern and colour from the child slot:

```
71F6  DE = (0xE122)                 ; sprite shadow write cursor
71FA  A = (IX+0x01) - 0x11; (DE) = A ; parent Y - 17
7200  A = (IX+0x02); (DE+1) = A      ; parent X
7205  HL = (IX+0x1B/1C); HL += 3     ; child's pattern byte
720F  (DE+2) = (HL); (DE+3) = (HL+1) ; pattern, then colour
```

So the two-tone effect costs one extra sprite slot per entity and is driven
entirely from the parent's coordinates — the child slot is never moved.

> **Open:** type 44's init sets `behaviour_flags = 0x03` (Y+X motion) but writes
> no velocity, and `random_x_pos` leaves Y at 0, so on this reading the entity
> would sit at the top of the screen. Either a velocity is set somewhere past
> 0x7213 (0x71F6's tail is not fully read) or by the caller. Worth resolving
> before porting type 44.

## Type → pattern table

| Type | Handler | Pattern | SAT_NAME | Sprite name | Color | Complement pat | Confidence | Notes |
|------|---------|---------|----------|-------------|-------|----------------|------------|-------|
| 1 | 0x75D5 | 14 | 0x38 | player_ship | 0x81/0x8F | — | confirmed | Color alternates during invincibility |
| 2 | 0x7221 | 10 (varies) | 0x28+ | shot_single (level 0) | 0x8F | — | confirmed | Pattern = (0xE10F); level 0 → 0x28 = pat10 |
| 3 | 0x7253 | varies | varies | fire weapon (ALL types 0–7) | varies | — | confirmed | **Universal fire weapon handler** — entity type 3 handles ALL 8 fire types (0xE14B selects behavior via dispatch tables at 0x7269/0x727F). Always slot 4 (0xE380). See fire weapon section below. |
| 4 | 0x7826 | 53 | 0xD4 | box | 0x8F | 54 (box_compl, 0xD8) | confirmed | SAT_NAME countdown before activation; vy_frac=0xC0 slow descent; complement 0xD8 |
| 5 | 0x7826 | 53 | 0xD4 | box | 0x8F | 54 (box_compl, 0xD8) | confirmed | Observed live; shorter countdown than type 6 |
| 6 | 0x7826 | 53 | 0xD4 | box | 0x8F | 54 (box_compl, 0xD8) | confirmed | Longer countdown; same init; +0x1D varies |
| 7 | 0x791D | 55 | 0xDC | umber_A | 0x8F | 57 (umber_complA, 0xE4) | likely | Init: `LD (IX+3),0xDC`, vy=3, Y-homing; complement 0xE4; when stopped: spawns 7 type-38 burst |
| 8 | 0x79BE | 55 | 0xDC | umber_A | 0x8B | 57 (umber_complA, 0xE4) | likely | Same init as type 7; color patched to 0x8B; when stopped: spawns 2 type-41 |
| 9 | 0x79FB | 56 | 0xE0 | umber_B | 0x83 | 58 (umber_complB, 0xE8) | likely | Same init as 7; pattern 0xE0 (pat 56) cyan; timer (+0x1D=8) periodically spawns type-20 |
| 10 | 0x7A2A | 22 | 0x58 | duster | 0x89 | 23 (duster_compl) | confirmed | `LD (ix+3),0x58`; complement SAT=0x5C seen in col-marker |
| 11 | 0x7AD4 | 10 | 0x28 | shot_single | — | — | confirmed | Base projectile spawner; type→69 after init |
| 12 | 0x7B07 | 24 | 0x60 | teruzo | 0x8A/0x89 | 25 (teruzo_compl, 0x64) | confirmed | **Path-follower, not a velocity enemy** - corner = `(type & 0xFE) + (R & 1)` into 0x7B63; direction script applied every 8 frames at speed 4. See [[teruzo_motion_tables]] and the correction below. |
| 13 | 0x7B07 | 24 | 0x60 | teruzo | 0x8A/0x89 | 25 (teruzo_compl, 0x64) | confirmed | Same handler; the low type bit is masked off (`AND 0xFE` at 0x7B13) - see below |
| 14 | 0x7B07 | 24 | 0x60 | teruzo | 0x89 | 25 (teruzo_compl, 0x64) | confirmed | Upper pair; blocks 0x7BAE/0x7BCC picked by the random bit - see below |
| 15 | 0x7B07 | 24 | 0x60 | teruzo | 0x89 | 25 (teruzo_compl, 0x64) | confirmed | (as 14) |
| 16 | 0x7BEB | 30 | 0x78 | luster_B | 0x8E | — | confirmed | **Corrected from pat 29→30.** Y-only fall bflags=0x01 vy=2; spawns col-marker; +0x1E=0xC0 |
| 17 | 0x7C8A | 30 | 0x78 | luster_B | 0x8E | — | confirmed | Same pattern as 16; bflags=0x13 Y+X+Xhom; vx=+3 rightward; tgt_x≈176 x_acc=64; +0x1E=0xE0 |
| 18 | 0x7CB3 | 29 | 0x74 | luster_A | 0x8B | — | confirmed | **Probe-confirmed.** bflags=0x13 Y+X+Xhom; vx=−1 leftward; color 0x8B (light-red); tgt_x=0xFF x_acc=14 |
| 19 | 0x74A4 | 9 | 0x24 | lg_circle | 0x80 | — | confirmed | Transient first-frame: init sets pat 9 color 0x80, then self-transitions type→0x83 (dispatches as type 3 on next frame) |
| 20 | 0x8668 | 7 | 0x1C | lead | ? | — | likely | `LD (ix+3),0x1C` |
| 21 | 0x8635 | 6 | 0x18 | light_bar | 0x84 | — | likely | `LD (IX+3),0x18`; color 0x84 confirmed live; bflags=0x03 Y+X motion vx=+2 |
| 22 | 0x7D0F | 33 | 0x84 | veybar_A | 0x83 | 38 (veybar_complA, 0x98) | likely | `LD (IX+3),0x84`; bflags=0x09 Y+Yhom; vy=4; R-bit: X=200 vx=−1 or X=40 vx=+1; +0x1D=80 |
| 23 | 0x7D0F | 33 | 0x84 | veybar_A | 0x83 | 38 (veybar_complA, 0x98) | likely | Same handler as 22; R-bit independently randomized |
| 24 | 0x7DB4 | 33 | 0x84 | veybar_A | 0x89 | 38 (veybar_complA, 0x98) | likely | bflags=0x1B Y+X+Yhom+Xhom; vy=4; R-bit: X=184 vx=−3 or X=56 vx=+3; +0x1D=88 |
| 25 | 0x7DB4 | 33 | 0x84 | veybar_A | 0x89 | 38 (veybar_complA, 0x98) | likely | Same as 24 |
| 35 | 0x8446 | 7/8/9/16/24 | 0x1C/0x20/0x24/0x40/0x60 | lead/med_circle/lg_circle/plane/teruzo | varies | — | confirmed | Pattern chosen from 0xE141; full sprite pool including teruzo (pat 24) observed. **NOT base-eye animator.** |
| 31/33 | 0x7F84 | 51 | 0xCC | stealth | 0x88 | 52 (stealth_compl, 0xD0) | confirmed | **Stealth jet tracker** — tracks player Y then X; fully visible (stealth jet shape). Col-marker uses stealth_compl. Random X from table 0x807C. |
| 34/65/66 | 0x7F99 | 51 | 0xCC | stealth | 0x88 | 52 (stealth_compl) | likely | Same init as 31/33 but stationary; fires 3-shot bursts on timer. Type-65 has color override (0x85). |
| 26 | 0x7DE2 | 43 | 0xAC | edge_swooper (unk) | 0x8E | +16 (pat 47) | hypothesis | 4-frame anim table 0x7E68 (pats 43,44,43,46); bflags=0x0F; spawns right X=200; complement = sat_name+0x10 |
| 27 | 0x7DF3 | 43 | 0xAC | edge_swooper (unk) | 0x8E | +16 (pat 47) | hypothesis | Same as 26; spawns left X=40 |
| 28 | 0x7E78 | 43 | 0xAC | edge_swooper (unk) | 0x87 | +16 (pat 47) | hypothesis | Anim table 0x7E70 (same pats, darker color 0x87); spawns right X=192 vx=−2 |
| 29 | 0x7E86 | 43 | 0xAC | edge_swooper (unk) | 0x87 | +16 (pat 47) | hypothesis | Same as 28; spawns left X=48 vx=+2 |
| 37 | 0x84DD | 7 | 0x1C | lead | 0x8F | — | confirmed | Enemy lead bullet; vy=−2 upward; bflags=0x03 Y+X motion |
| 39 | 0x8525 | 17/23/25 | 0x44/0x5C/0x64 | plane_compl/duster_compl/teruzo_compl | 0x81 | — | confirmed | Complement sprite matches parent type: plane→plane_compl, duster→duster_compl, teruzo→teruzo_compl |
| 40 | 0x852C | 10 | 0x28 | shot_single | 0x8F | — | hypothesis | Observed live briefly; handler = `JP entity_clear` (transient slot) |
| 44 | 0x82D0 | 16 | 0x40 | plane | 0x83 | 17 (plane_compl) | confirmed | Main ground structure; complement via col-marker |
| 56 | 0x819D | 28 | 0x70 | sig_single | 0x86↔0x8F | — | confirmed | Color XOR 0x09 each frame (flashing); falling pickup/missile |
| 68 | 0x77A1 | (converts) | — | proto-box | — | — | confirmed | **The box-wave spawner**: converts itself into a wave of three disguised boxes (types from the score-digit row `0x77EA + (0xE104 & 0x0F)*3`, disguise countdowns from `0x7808 + (0xE105 >> 4)*3`, X random in [0x38,0x77] stepping +0x20). "Sprite computed from score" was a misreading of these two table lookups; the entity itself never draws. Spawned by the every-16th-kill trigger (0xE125). |
| 69 | 0x7A67 | 7 | 0x1E | lead | 0x00 | — | confirmed | Base projectile (running); spawned by type 11; initially transparent |
| 75 | 0x8A5A | 7 | 0x1C | lead | 0x00 | — | confirmed | Base-gated entity (types 73–79 group); lead bullet, initially transparent |
| 82/87 | 0x87AB | 9 | 0x24 | large_circle | ? | — | likely | Wide ground structure; `LD (ix+3),0x24` |

## Color encoding (TMS9918A)

Color byte in SAT: `0xF0 = EC flag (early clock); 0x0F = color 0–15`.
Common values: 0x8F = white (EC+15), 0x83 = cyan (EC+3), 0x89 = light-blue (EC+9),
0x8B = light-red (EC+11), 0x81 = black (EC+1, used for complement sprites — near-transparent dark tint).

## Type 35 correction

Sprint 0012 labeled handler 0x8446 as `handler_type35_base_eye`. Live capture
shows type 35 entities use patterns 7/8/9/16 at visible screen positions — not
base-eye behaviour. The handler reads `(0xE141)` (a game-state counter) to pick a
pattern from the lead/circle/plane range. Corrected label: `handler_type35_projectile`.
The `0xBFAB` call from this handler is a position-update side-effect, not the
primary purpose.

## Types 12–15 design note

All four share handler 0x7B07 and the **hardcoded** `LD (IX+0x03), 0x60` at 0x7B4D
giving teruzo (pat 24) for every variant. The "sub-handler" addresses in the subtable
at 0x7B63 entries [12–15] are **data pointers**, not code — the handler reads 3 bytes
from them as (Y, X, color):

| Entry addr | Types | Y | X | Color |
|---|---|---|---|---|
| 0x7B83 | 12 varA | 112 | 208 | 0x8A |
| 0x7B98 | 13 varB | 112 | 16  | 0x8A |
| 0x7BAE | 14 varA | 32  | 208 | 0x89 |
| 0x7BCC | 15 varB | 32  | 16  | 0x89 |

The R-register random bit selects varA (right, X=208) or varB (left, X=16).
Types 12/13 spawn lower (Y=112, color 0x8A); types 14/15 spawn higher (Y=32, color 0x89).
The complement sprite for all teruzo variants is teruzo_compl (pat 25, SAT=0x64), confirming
the column-marker / complement-sprite duality.

## Patterns that cycle / animate

Entities using `entity_update` bit2 animation (sprint 0021/0024 confirmed): the animation
routine at 0x4912 reads a ROM table at IX+0x11:+0x12 and cycles (sat_name, sat_color) pairs.

**Type 35** (enemy projectile) — table at 0x84D1, 6 frames, tick_rate=4, init +0x0F=1:

| Frame | sat_name | Pattern | Sprite | sat_color | Note |
|-------|---------|---------|--------|-----------|------|
| 0 | 0xD0 | 52 | stealth_compl | 0x48 | Overlaps `JP 0x48D0` bytes — never shown (init skips to frame 1) |
| 1 | 0x1C | 7 | lead | 0x8A dark-blue | Loop start |
| 2 | 0x20 | 8 | med_circle | 0x8E light-green | |
| 3 | 0x24 | 9 | lg_circle | 0x8F white | Peak |
| 4 | 0x20 | 8 | med_circle | 0x8D | |
| 5 | 0x1C | 7 | lead | 0x89 light-blue | Loop end → wrap to 0 |

Effect: lead→circle pulsing animation; projectile appears to "breathe." After frame 5 wraps to frame 0, the stealth_compl flash is a brief dark flicker before restarting at frame 1.

**Type 60** (player death explosion) — table at 0x86F3, 11 frames, tick_rate=4, +0x0C=0x04 (bit2 only, no motion):

| Frame | sat_name | Pattern | Sprite | sat_color |
|-------|---------|---------|--------|-----------|
| 0 | 0x00 | 0 | empty (invisible) | 0xC9 (EC+9, overlaps code byte) |
| 1 | 0x1C | 7 | lead | 0x86 |
| 2 | 0x1C | 7 | lead | 0x8F white |
| 3 | 0x20 | 8 | med_circle | 0x88 |
| 4 | 0x20 | 8 | med_circle | 0x8F white |
| 5 | 0x24 | 9 | lg_circle | 0x89 |
| 6 | 0x24 | 9 | lg_circle | 0x8F white |
| 7 | 0x20 | 8 | med_circle | 0x88 |
| 8 | 0x20 | 8 | med_circle | 0x89 |
| 9 | 0x1C | 7 | lead | 0x86 |
| 10 | 0x1C | 7 | lead | 0x8F white |

Effect: expanding-then-contracting explosion (invisible → lead → circle → lg_circle → circle → lead → invisible). No motion flags set — explosion stays at player's last position. Observed in slot 0 during player death sequence.

**Entities with manual animation (not via bit2):**
- Type 35: initial sat_name chosen at spawn from 0xE141 (lead/circle/plane range); then bit2 cycles the above table
- Type 6 (init): decrementing SAT_NAME 0x20→0x00 gives patterns 8→0 (countdown animation)
- Type 3: same pattern 9, all 16 colors (0x80–0x8F) cycled in handler code directly

## Fire weapon system — type 3 handler (sprint 0023)

Entity type 3 (handler 0x7253) handles **all 8 fire weapon types**. Fire type selected
by `fire_type` (0xE14B, 0–7). Always spawned in entity slot 4 (0xE380) by the player
handler. The handler dispatches per fire_type via `sub_5C2E` (0x5C2E).

### sub_5C2E — computed dispatch

Classic Z80 stack trick: pops the return address into HL, adds fire_type×2 as index,
reads a 16-bit LE target from the inline table, pushes it as the new return address,
and executes RET. The dispatch table follows immediately after the CALL instruction.

### Dispatch tables (8 entries × 2 bytes each, LE addresses)

**Init dispatch** (at 0x7269, called once when entity first becomes active):

| fire_type | Weapon | Init handler |
|-----------|--------|-------------|
| 0 | All-Range Cannon | 0x72B3 |
| 1 | Straight Crasher | 0x72A8 |
| 2 | Field Shutter | 0x729D |
| 3 | Circular | 0x7331 |
| 4 | Vibrator | 0x73CE |
| 5 | Rewinder | 0x73C8 |
| 6 | Plasma Flash | 0x73CE (shared with Vibrator) |
| 7 | High Speed | 0x728F |

**Running dispatch** (at 0x727F, called every frame):

| fire_type | Weapon | Run handler |
|-----------|--------|------------|
| 0 | All-Range Cannon | 0x72DE |
| 1 | Straight Crasher | 0x72EA |
| 2 | Field Shutter | 0x72F5 |
| 3 | Circular | 0x735D |
| 4 | Vibrator | 0x7439 |
| 5 | Rewinder | 0x7464 |
| 6 | Plasma Flash | 0x7494 |
| 7 | High Speed | 0x7306 |

### Per-weapon behavior (confirmed from ROM + live capture)

| fire_type | Sprite (+0x0C) | Behavior |
|-----------|---------------|---------|
| 0 All-Range | pattern 3 (target), +0x0C=0x03 | Run: INC sat_color AND 0x8F (16-color cycle); motion from velocity table 0x7758 via 4CF7 |
| 1 Straight | same color cycle pattern; +0x0C=0x01 | Run: CALL type-0 run (color + motion), then ammo-limit check → despawn |
| 2 Field Shutter | +0x0C=0x01 | Run: Y=player_Y−8, X=player_X (follows player!) |
| 3 Circular | pattern 4 (snowflake), +0x0C=0x00 | Run: decrements position counter in +0x11, orbs follow player manually |
| 4 Vibrator | pattern 4 (snowflake), +0x0C=0x01 | Shares init with Plasma Flash |
| 5 Rewinder | +0x0C=0x01 | Similar to Straight |
| 6 Plasma Flash | shares Vibrator init (0x73CE) | Separate run code at 0x7494; no persistent entity observed (immediate effect) |
| 7 High Speed | +0x0C varies | Run: decrements 0xE14C timer; CALL 0x730B |

### sub_7548 — fire weapon switcher (called after 5 max power chips)

```
7548: LD E, A            ; save new fire_type
7549: LD HL, 0xE14B      ; → fire_type
754C: LD D, (HL)         ; D = old fire_type
754D: LD (HL), A         ; update fire_type
754E: ADD A,A; LD C,A    ; C = new_type × 2
7552: LD HL, 0x751F      ; fire weapon limit table (8 × 2 bytes)
7555: ADD HL,BC          ; index
7556: LD A, 0x3C         ; 60 decimal
7558: LD (0xE14C), A     ; reset primary limit display
755B: LD A,(HL); LD (0xE14D),A   ; limit byte 0 from table
7560: LD A,(HL+1); LD (0xE14E),A ; limit byte 1 from table
7564: if fire_type=2 (FieldShutter): special handling
756C: if new_type ≠ old_type: LD (0xE380), 0x28 → despawn current fire entity (type 40)
```

**Limit table at 0x751F** (bytes 0–1 per fire type = 0xE14D, 0xE14E values):

| fire_type | Byte0 | Byte1 | Interpretation |
|-----------|-------|-------|----------------|
| 0 All-Range | 0x00 | 0x02 | Infinite (0x00 flag?) |
| 1 Straight  | 0x64 | 0x03 | 100 shots, 3? |
| 2 Field     | 0x64 | 0x01 | 100 durability |
| 3 Circular  | 0xC8 | 0x01 | 200 time units |
| 4 Vibrator  | 0x1E | 0x01 | 30 durability |
| 5 Rewinder  | 0x64 | 0x03 | 100, 3? |
| 6 Plasma    | 0x0F | 0x03 | 15 ammo (very limited) |
| 7 HighSpeed | 0xFA | 0x03 | 250 time units, 3? |

## Type 60 — player death explosion

| Type | Handler | Pattern | SAT_NAME | Sprite | Color | +0x0C | Confidence |
|------|---------|---------|----------|--------|-------|-------|------------|
| 60 | 0x869E | 7/8/9 (animated) | 0x1C→0x24 | lead/circle/lg_circle | varies | 0x04 (bit2 only) | confirmed |

Type 60 is the player death explosion entity. Spawned in slot 0 when the player is destroyed.
Handler at 0x869E. Uses entity_update bit2 animation with 11-frame table at 0x86F3.

| 36 | 0x8296 | 13 | 0x34 | flicker (unk) | 0x8F | — | confirmed | Spawns near top Y≈13; slow descent vy_frac=0x80; running code XORs color with 0x0E each frame |
| 42 | 0x85CC | 7 | 0x1C | lead | 0x8F | — | confirmed | **Self-transforms to type 37** on init; proto-bullet converter |
| 43 | 0x85D6 | 7 | 0x1C | lead | 0x8F | — | confirmed | **Self-transforms to type 38** on init; proto-fragment converter |
| 45 | 0x85EE | 6 | 0x18 | light_bar | 0x8F | — | confirmed | light_bar variant (white); bflags=0x03 Y+X vx=+1; +0x19=3 |
| 57 | 0x81D1 | 27 | 0x6C | descender_A | 0x8F | 26? | confirmed | Paired with type 58; vy≈2.5 downward; spawns col-marker; +0x1F=7 |
| 58 | 0x8247 | 26 | 0x68 | descender_B | 0x8F | 27? | confirmed | Paired with type 57; vy≈2.5; spawns col-marker; +0x1E=0xE4 +0x1F=7 |
| 59 | 0x8269 | 28 | 0x70 | sideways (unk) | 0x8F | — | confirmed | Moves right vx≈2.5 (bflags=0x03 but vy=0); +0x1F=0x20 |
| 61 | 0x8302 | 62 | 0xF8 | large_A (unk) | 0x83 | — | confirmed | Large pattern index; Y-only vy=2; spawns col-marker col_wid=1; +0x1E=32 |
| 62 | 0x8709 | 0 | 0x00 | (invisible) | 0x87 | — | confirmed | No sprite; vy=−1 upward; likely non-visual trigger or effect entity |
| 64 | 0x8279 | 16 | 0x40 | plane | 0x83 | 17 (plane_compl) | confirmed | **Self-transforms to type 44** on init; proto-structure converter; cyan |
| 67 | 0x839F | 8 | 0x20 | med_circle | 0x86 | — | confirmed | bflags=0x03 Y+X; color 0x86 dark; +0x19=5 |

## Patterns still unknown

Types 18, 36, 38, 41–43, 45–55, 57–67, 70–74, 76–81, 83–86, 88–89
are not yet mapped.

**Partially known (hypothesis):** types 26–29 use patterns 43–46 (edge-swooper sprites, SAT_NAME 0xAC–0xB8) — sprite graphics not yet decoded, name unknown.

**Removed from unknown list (this sprint):** types 16–18 (luster family corrected + confirmed), 36 (flicker), 42–43 (proto-converters), 45 (light_bar), 57–59 (descender pair + sideways), 61–62 (large/invisible), 64 (proto-structure), 67 (med_circle).

**Previously removed:** types 4–6 (box), 9 (umber_B), 12–13 directions, 21 color, 22–25 (veybar), 37 (lead bullet), 60 (death explosion).

**New patterns seen but unnamed:** 13 (type 36 flicker), 26/27 (types 58/57 descender pair), 28 (type 59 sideways), 30 (types 16/17 luster_B), 62 (type 61 large).
