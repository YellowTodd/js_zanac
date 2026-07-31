/**
 * Entity framework: the 26-slot pool at 0xE300 and the shared per-frame update.
 *
 * Ported from subsystem C (kb/data/entity_table.md):
 *   entity_update  0x4898   behaviour_flags dispatch + sprite push
 *   entity_clear   0x48D0   partial zero (only +0x00..+0x17)
 *
 * Slots are 32 bytes; byte 0 holds the type in bits 0-6 and the active flag in
 * bit 7. Bytes +0x18..+0x1F deliberately survive `entityClear`, matching the
 * original's 24-byte wipe.
 */

export const ENTITY_SLOTS = 26;
export const ENTITY_STRIDE = 32;

/** Slot roles (kb/data/entity_table.md "Entity type roles"). */
export const SLOT_PLAYER = 0;
export const SHOT_SLOT_FIRST = 1;
/**
 * Shots own slots 1-3 only (0xE320/0xE340/0xE360): `collision_dispatch`'s
 * shot pass (0x44F9) tests exactly those three, and slot 4 (0xE380) is the
 * fire-weapon slot with its own gate. entity_table.md's "slots 1-4" is
 * wrong - a fourth shot there would overwrite the fire entity.
 */
export const SHOT_SLOT_LAST = 3;
/** 0xE380: the fire-weapon entity slot (type 3). */
export const FIRE_SLOT = 4;
/** General entity pool scanned by both allocators: slots 5..25. */
export const STRUCT_POOL_FIRST = 5;
export const STRUCT_POOL_LAST = 25;

export const TYPE_PLAYER = 0x01;
export const TYPE_SHOT = 0x02;
export const TYPE_FIRE = 0x03;

/** behaviour_flags bits (+0x0C). */
export const BEH_Y_MOTION = 0x01;
export const BEH_X_MOTION = 0x02;
export const BEH_ANIMATE = 0x04;
export const BEH_Y_HOMING = 0x08;
export const BEH_X_HOMING = 0x10;

/** Y at or beyond this despawns a moving entity (0x48DE). */
const DESPAWN_Y = 208;
/** SAT rows are the entity Y minus this (sprite bottom-edge encoding). */
export const SPRITE_Y_BIAS = 17;

/** Sprite shadow: 32 records of 4 bytes, flushed to the SAT each frame. */
export const MAX_SPRITES = 32;

export class EntityPool {
  constructor() {
    this.slots = new Uint8Array(ENTITY_SLOTS * ENTITY_STRIDE);
    /** Sprite shadow buffer (the 0xE122 write cursor's target). */
    this.sprites = new Uint8Array(MAX_SPRITES * 4);
    /** Number of sprite records pushed this frame (0xE11F). */
    this.spriteCount = 0;
  }

  reset() {
    this.slots.fill(0);
    this.spriteCount = 0;
  }

  base(slot) {
    return slot * ENTITY_STRIDE;
  }

  type(slot) {
    return this.slots[slot * ENTITY_STRIDE] & 0x7f;
  }

  active(slot) {
    return this.slots[slot * ENTITY_STRIDE] !== 0;
  }

  /** `entity_clear` (0x48D0): zero +0x00..+0x17 only. */
  clear(slot) {
    const b = slot * ENTITY_STRIDE;
    this.slots.fill(0, b, b + 0x18);
  }

  /**
   * `alloc_entity_slot` (0x4496): the general pool allocator - scan **forward**
   * from slot 5 (0xE3A0) over 21 slots, returning the first inactive one.
   *
   * Note it runs the opposite way to `check_col_clear` (0x9B22), which walks
   * slot 25 downward for the same pool. Airborne spawns therefore fill from the
   * bottom of the range while ground structures fill from the top, so the two
   * only contend once the pool is nearly full.
   */
  allocEntitySlot() {
    return this.findFree(STRUCT_POOL_FIRST, STRUCT_POOL_LAST);
  }

  /** First free slot in [first, last], or -1. */
  findFree(first, last) {
    for (let slot = first; slot <= last; slot++) {
      if (this.slots[slot * ENTITY_STRIDE] === 0) return slot;
    }
    return -1;
  }

  /** Begin a frame's sprite list. */
  beginFrame() {
    this.spriteCount = 0;
  }

  /** Push one sprite record, as the tail of `entity_update` does. */
  pushSprite(y, x, name, color) {
    if (this.spriteCount >= MAX_SPRITES) return;
    const i = this.spriteCount++ * 4;
    this.sprites[i] = y & 0xff;
    this.sprites[i + 1] = x & 0xff;
    this.sprites[i + 2] = name;
    this.sprites[i + 3] = color;
  }

  /** Copy the shadow into the screen's sprite attribute table. */
  flushSprites(screen) {
    screen.hideSprites();
    for (let i = 0; i < this.spriteCount; i++) {
      const s = i * 4;
      screen.setSprite(
        i,
        this.sprites[s],
        this.sprites[s + 1],
        this.sprites[s + 2],
        this.sprites[s + 3]
      );
    }
  }
}

/** Read a slot's 16-bit fixed-point pair as a signed value. */
function pair(slots, b, hi, lo) {
  const v = (slots[b + hi] << 8) | slots[b + lo];
  return v >= 0x8000 ? v - 0x10000 : v;
}

/**
 * `entity_update` (0x4898): homing, motion, animation, then the sprite push.
 *
 * Note the field order the KB records: +0x08/+0x09 are the **Y** velocity
 * fraction/integer and +0x0A/+0x0B the X pair, matching `entity_table.md`.
 *
 * @param {EntityPool} pool
 * @param {number} slot
 * @param {import('../assets.js').DataRom} rom
 */
export function entityUpdate(pool, slot, rom) {
  const s = pool.slots;
  const b = slot * ENTITY_STRIDE;
  const beh = s[b + 0x0c];

  if (beh & BEH_Y_HOMING) home(s, b, 0x13, 0x15, 0x09, 0x08, 0x01);
  if (beh & BEH_X_HOMING) home(s, b, 0x14, 0x16, 0x0b, 0x0a, 0x02);

  if (beh & BEH_Y_MOTION) {
    const pos = ((s[b + 0x01] << 8) | s[b + 0x06]) + pair(s, b, 0x09, 0x08);
    s[b + 0x01] = (pos >> 8) & 0xff;
    s[b + 0x06] = pos & 0xff;
    if (s[b + 0x01] >= DESPAWN_Y) {
      pool.clear(slot);
      return;
    }
  }
  if (beh & BEH_X_MOTION) {
    const pos = ((s[b + 0x02] << 8) | s[b + 0x07]) + pair(s, b, 0x0b, 0x0a);
    s[b + 0x02] = (pos >> 8) & 0xff;
    s[b + 0x07] = pos & 0xff;
    if (s[b + 0x02] >= 209) {
      pool.clear(slot);
      return;
    }
  }

  if (beh & BEH_ANIMATE) {
    s[b + 0x0d] = (s[b + 0x0d] - 1) & 0xff;
    if (s[b + 0x0d] === 0) {
      s[b + 0x0d] = s[b + 0x0e];
      s[b + 0x0f] = (s[b + 0x0f] + 1) % (s[b + 0x10] || 1);
      const table = s[b + 0x11] | (s[b + 0x12] << 8);
      s[b + 0x03] = rom.byte(table + s[b + 0x0f] * 2);
      s[b + 0x04] = rom.byte(table + s[b + 0x0f] * 2 + 1);
    }
  }

  pushEntitySprite(pool, slot);
}

/** Shared homing step: nudge a velocity toward a target, +0x17 times. */
function home(s, b, targetOff, accelOff, velHi, velLo, axis) {
  const iterations = s[b + 0x17];
  const posOff = axis === 1 ? 0x01 : 0x02;
  for (let i = 0; i < iterations; i++) {
    const delta = s[b + targetOff] - s[b + posOff];
    if (delta === 0) break;
    let vel = (s[b + velHi] << 8) | s[b + velLo];
    if (vel >= 0x8000) vel -= 0x10000;
    vel += delta > 0 ? s[b + accelOff] : -s[b + accelOff];
    s[b + velHi] = (vel >> 8) & 0xff;
    s[b + velLo] = vel & 0xff;
  }
}

/** The unconditional SAT push at the tail of `entity_update`. */
export function pushEntitySprite(pool, slot) {
  const s = pool.slots;
  const b = slot * ENTITY_STRIDE;
  if (s[b + 0x01] === 0) return; // y = 0 means "no sprite"
  pool.pushSprite(s[b + 0x01] - SPRITE_Y_BIAS, s[b + 0x02], s[b + 0x03], s[b + 0x04]);
}
