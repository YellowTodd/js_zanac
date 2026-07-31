/**
 * Software sprite collision.
 *
 * Ported from subsystem C:
 *   hitbox_setup_ix     0x45A0  bounds for the entity under test
 *   hitbox_check_iy     0x4560  overlap against those bounds
 *   collision_size_table 0x45C9 half-sizes indexed by sat_name >> 1
 *   entity_post         0x44BA  bounds, then player and shot dispatchers
 *   check_col_clear     0x9B22  ground-structure slot allocator + blocked test
 */

import { ENTITY_STRIDE, SLOT_PLAYER, SHOT_SLOT_FIRST, SHOT_SLOT_LAST, FIRE_SLOT } from './entity.js';

const COLLISION_SIZE_TABLE = 0x45c9;
/** Sprites are 16x16, so bounds are built around a 16-pixel cell. */
const SPRITE_SPAN = 0x10;
/** Either axis at or past this is off-play and cannot collide (0x4570). */
const OFF_SCREEN = 0xf0;

/** Ground-structure scan range used by `check_col_clear`: slots 25 down to 5. */
export const STRUCT_SLOT_FIRST = 5;
export const STRUCT_SLOT_LAST = 25;
/** Types `check_col_clear` treats as passable / blocking. */
const PASSABLE_TYPES = new Set([0x14, 0x25, 0x26]);
const BLOCKING_MARKER = 0x27;
const BLOCKING_WIDE = 0x46;

/**
 * `hitbox_setup_ix` (0x45A0). The two edges per axis are `pos + half` and
 * `pos + 16 - half`; with half < 8 the first is the smaller, so the pair is an
 * interval, not a bottom/top in screen order.
 */
export function hitbox(slots, base, rom) {
  const index = slots[base + 0x03] >> 1;
  const halfY = rom.byte(COLLISION_SIZE_TABLE + index);
  const halfX = rom.byte(COLLISION_SIZE_TABLE + index + 1);
  const y = slots[base + 0x01];
  const x = slots[base + 0x02];
  return {
    yLo: (y + halfY) & 0xff,
    yHi: (y + SPRITE_SPAN - halfY) & 0xff,
    xLo: (x + halfX) & 0xff,
    xHi: (x + SPRITE_SPAN - halfX) & 0xff,
  };
}

/**
 * `hitbox_check_iy` (0x4560): does the entity at `base` overlap `bounds`?
 *
 * The assembly splits into "my low edge is inside their interval" and "my low
 * edge is below theirs but my high edge reaches it", which together are the
 * plain interval overlap reproduced here.
 */
export function hitboxOverlaps(slots, base, rom, bounds) {
  const y = slots[base + 0x01];
  const x = slots[base + 0x02];
  if (y >= OFF_SCREEN || x >= OFF_SCREEN) return false;

  const index = slots[base + 0x03] >> 1;
  const halfY = rom.byte(COLLISION_SIZE_TABLE + index);
  const halfX = rom.byte(COLLISION_SIZE_TABLE + index + 1);

  const yLo = (y + halfY) & 0xff;
  const yHi = (y + SPRITE_SPAN - halfY) & 0xff;
  if (!(yLo < bounds.yHi && yHi >= bounds.yLo)) return false;

  const xLo = (x + halfX) & 0xff;
  const xHi = (x + SPRITE_SPAN - halfX) & 0xff;
  return xLo < bounds.xHi && xHi >= bounds.xLo;
}

/**
 * `check_col_clear` (0x9B22): scan slots 25 down to 5 for a free slot, and
 * report whether a blocking structure already owns the column.
 *
 * The routine doubles as the allocator - phase 1 stops at the first inactive
 * slot and returns with HL still pointing at it.
 *
 * @returns {{slot: number, blocked: boolean}} slot is -1 when the pool is full
 */
export function checkColClear(pool) {
  const s = pool.slots;
  for (let slot = STRUCT_SLOT_LAST; slot >= STRUCT_SLOT_FIRST; slot--) {
    if (s[slot * ENTITY_STRIDE] === 0) return { slot, blocked: false };
  }
  // Pool full: decide passable vs blocking from the occupying types.
  for (let slot = STRUCT_SLOT_LAST; slot >= STRUCT_SLOT_FIRST; slot--) {
    const type = s[slot * ENTITY_STRIDE] & 0x7f;
    if (PASSABLE_TYPES.has(type)) return { slot: -1, blocked: false };
    if (type === BLOCKING_MARKER || type >= BLOCKING_WIDE) return { slot: -1, blocked: true };
  }
  return { slot: -1, blocked: true };
}

/** `death_transition_table` (0x716B): type -> post-collision type, 90 entries. */
const DEATH_TRANSITION_TABLE = 0x716b;
/** Post-collision types whose handler is documented as a plain despawn. */
const TYPE_DESPAWN = 40;

/**
 * `collision_response` (0x453E): remap **both** parties through
 * `death_transition_table`, having first stashed the current entity's original
 * type in +0x18 so the death handler can still award the right score.
 *
 * @param {import('./entity.js').EntityPool} pool
 * @param {import('../assets.js').DataRom} rom
 * @param {number} ixSlot the entity being tested
 * @param {number} iySlot the shot or player that hit it
 */
export function collisionResponse(pool, rom, ixSlot, iySlot) {
  const s = pool.slots;
  const ix = ixSlot * ENTITY_STRIDE;
  const iy = iySlot * ENTITY_STRIDE;

  const ixType = s[ix] & 0x7f;
  s[ix + 0x18] = ixType;
  s[ix] = rom.byte(DEATH_TRANSITION_TABLE + ixType);

  const iyType = s[iy] & 0x7f;
  s[iy] = rom.byte(DEATH_TRANSITION_TABLE + iyType);

  // Type 40's handler is `entity_clear`, so resolve it here rather than
  // leaving a slot occupied by an entity whose only job is to vanish. The
  // other death targets - 19, 35, 60 and 80 - all have real handlers, so they
  // are left alone to run their animations and scoring.
  for (const slot of [ixSlot, iySlot]) {
    const type = pool.slots[slot * ENTITY_STRIDE] & 0x7f;
    if (type === TYPE_DESPAWN || type === 0 || !HANDLED_DEATH_TYPES.has(type)) {
      pool.clear(slot);
    }
  }
}

/** Post-collision types this port has a real handler for (none yet). */
const HANDLED_DEATH_TYPES = new Set([19, 35, 60, 80]);

/**
 * `entity_post` for one entity: test it against the player and the player's
 * shots.
 *
 * There are **two entry points with different fire-weapon gates**, and they
 * are easy to conflate:
 *
 * - 0x44BA (airborne enemies, boxes) runs `collision_dispatch` (0x44D4),
 *   which admits the fire slot when 0xE14E **bit 0** is set, and also tests
 *   the player.
 * - 0x44CA (ground structures, base segments) drops straight into the
 *   shots-only sweep (0x44F9); its tail at **0x4526 tests bit 1** instead,
 *   and never tests the player.
 *
 * The distinction is load-bearing: fire 0 - the weapon the player starts with
 * - has mode 0x02, so it hits **ground structures only**. Gate it on bit 0
 * and shooting a statue with the default fire does nothing at all.
 *
 * @param {boolean} [groundPath] use the 0x44CA gate (bit 1) instead of bit 0
 * @returns {{hitBy: number}|null} the slot that hit it, or null
 */
export function checkEntityCollisions(pool, rom, slot, fireMode, groundPath = false) {
  const base = slot * ENTITY_STRIDE;
  if (pool.slots[base + 0x01] === 0) return null; // no sprite, no hitbox
  const bounds = hitbox(pool.slots, base, rom);

  for (let other = SHOT_SLOT_FIRST; other <= SHOT_SLOT_LAST; other++) {
    if (!pool.active(other)) continue;
    if (hitboxOverlaps(pool.slots, other * ENTITY_STRIDE, rom, bounds)) {
      return { hitBy: other };
    }
  }
  // 0x44D4 / 0x4526: the fire slot collides only while the weapon's mode byte
  // (0xE14E) has this entry's bit set and the slot holds an active type 3.
  if (
    fireMode !== undefined &&
    (fireMode & (groundPath ? 0x02 : 0x01)) !== 0 &&
    pool.slots[FIRE_SLOT * ENTITY_STRIDE] === 0x83 &&
    hitboxOverlaps(pool.slots, FIRE_SLOT * ENTITY_STRIDE, rom, bounds)
  ) {
    return { hitBy: FIRE_SLOT };
  }
  // Only a *living* player is a collision target - confirmed at 0x44EA:
  // collision_dispatch does `LD A,(0xE300); CP 0x81` and skips the check for
  // anything else, so a ship mid-death (type 60) cannot be re-hit. The shot
  // slots are gated the same way with `CP 0x82` (0x4500/0x450F/0x451E).
  if (pool.type(SLOT_PLAYER) === 0x01) {
    const playerBase = SLOT_PLAYER * ENTITY_STRIDE;
    // +0x05 bit 7 is the spawn invincibility flag.
    if ((pool.slots[playerBase + 0x05] & 0x80) === 0) {
      if (hitboxOverlaps(pool.slots, playerBase, rom, bounds)) return { hitBy: SLOT_PLAYER };
    }
  }
  return null;
}
