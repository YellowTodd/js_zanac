/**
 * Player ship and the normal shot.
 *
 * Ported from subsystem F:
 *   read_player_input     0x4343  input byte 0xE100 + direction selector 0xE10C
 *   set_velocity_from_dir 0x4CF7  direction + speed -> velocity pair
 *   player_ship_handler   0x75D5  spawn / respawn into slot 0
 *   player_ship_update    0x7612  move, shoot, write the sprite
 *   shot_handler          0x7221  the type-2 shot entity
 *   load_shot_params      0x7771  shot_level -> speed / cap / sprite
 */

import { IN_UP, IN_DOWN, IN_LEFT, IN_RIGHT, IN_SHOT } from '../input.js';
import {
  ENTITY_STRIDE,
  SLOT_PLAYER,
  SHOT_SLOT_FIRST,
  FIRE_SLOT,
  TYPE_PLAYER,
  TYPE_SHOT,
  BEH_Y_MOTION,
  entityUpdate,
  pushEntitySprite,
} from './entity.js';
import { runTypeHandler, postTypeHandler } from './enemy.js';
import { placeWaveRecord } from './scroll.js';

/** `xvel_table` (0x7758): direction selector 0xE10C -> 16-way direction. */
const XVEL_TABLE = 0x7758;
/**
 * `vel_dir_table` (0x4D65): 16 unit vectors of magnitude 128, four bytes each.
 *
 * The pairs are **(Y, X)**, not (X, Y): the first word lands in +0x08/+0x09,
 * which `entity_table.md` documents as the Y velocity. `set_velocity_from_dir.md`
 * labels them the other way round, which inverts every diagonal — with (Y, X)
 * all eight directions agree with `xvel_table` and the 0x43A0 selector maths.
 */
const VEL_DIR_TABLE = 0x4d65;
/** `shot_power_table` (0x778F): 3 bytes per shot level. */
const SHOT_POWER_TABLE = 0x778f;
/** `shot_rate_table` (0x7761): firing cadence -> ALC spawn advance. */
const SHOT_RATE_TABLE = 0x7761;

/** The selector value that means "no direction held" (0x43A0 seeds 4). */
const DIR_CENTRED = 4;
/** Ship movement clamps from `player_ship_update`. */
const SHIP_Y_MIN = 0x1e;
const SHIP_Y_MAX = 0xb8;
const SHIP_X_MIN = 0x28;
const SHIP_X_MAX = 0xc8;
/** Fixed 20-frame auto-fire period (0xE110 reload). */
const SHOT_PERIOD = 0x14;
/** Player speed byte (+0x17): five steps of the unit vector, no prescale. */
const SHIP_SPEED = 5;

/** Spawn state for slot 0, from `player_ship_handler` (0x75D5). */
const SHIP_SPAWN = {
  y: 0xa0,
  x: 0x78,
  satName: 0x38,
  satColor: 0x8f,
  invincibility: 0x40,
};

export class PlayerState {
  constructor() {
    /** 0xE10B shot power level (0-5). */
    this.shotLevel = 0;
    /** 0xE10C direction selector. */
    this.dirSelector = DIR_CENTRED;
    /** 0xE10D/E/F, loaded from shot_power_table. */
    this.shotCap = 2;
    this.shotSpeed = 4;
    this.shotSprite = 0x28;
    /** 0xE110 auto-fire cooldown. */
    this.shotCooldown = 0;
    /** 0xE13F frames since the last shot, indexes shot_rate_table. */
    this.fireCadence = 0;
    /** 0xE140/0xE141 ALC counters. */
    this.shotsFired = 0;
    this.fireEvents = 0;
    /** 0xE14F: maxed-chip counter (every 5th refreshes the fire). */
    this.maxedChips = 0;
    /** 0xE14B..0xE14E fire-weapon state. */
    this.fireNum = 0;
    this.fireCounter = 0;
    this.fireMode = 2;
    this.fireFrame = 0x3c;
  }
}

/**
 * `load_shot_params` (0x7771): the three bytes of `shot_power_table` for the
 * current level. Note levels 0 and 1 share sprite 0x28, so the shot only
 * grows its second stream at level 2 - one power chip raises LEVEL and the
 * firing rate, two are needed before it looks different.
 */
export function loadShotParams(player, rom) {
  const entry = SHOT_POWER_TABLE + 3 * (player.shotLevel & 0x0f);
  player.shotSpeed = rom.byte(entry); // 0x7780 -> 0xE10E
  player.shotCap = rom.byte(entry + 1); // 0x7784 -> 0xE10D
  player.shotSprite = rom.byte(entry + 2); // 0x7789 -> 0xE10F
}

/**
 * `read_player_input` (0x43A0 tail): fold the active-low input byte into the
 * direction selector. Base 4, +1 up, -1 down, -3 left, +3 right.
 */
export function directionSelector(inputState) {
  let a = DIR_CENTRED;
  if ((inputState & IN_UP) === 0) a += 1;
  if ((inputState & IN_DOWN) === 0) a -= 1;
  if ((inputState & IN_LEFT) === 0) a -= 3;
  if ((inputState & IN_RIGHT) === 0) a += 3;
  return a & 0xff;
}

/**
 * `set_velocity_from_dir` (0x4CF7): unit vector for `dir`, prescaled by the
 * speed byte's bits 6/7 and repeated by its low six bits.
 */
export function setVelocityFromDir(slots, base, rom, dir, speed) {
  const entry = VEL_DIR_TABLE + 4 * (dir & 0x0f);
  let vy = rom.byte(entry) | (rom.byte(entry + 1) << 8);
  let vx = rom.byte(entry + 2) | (rom.byte(entry + 3) << 8);
  if (vy >= 0x8000) vy -= 0x10000;
  if (vx >= 0x8000) vx -= 0x10000;

  // 0x4D0D: bit 6 is **x3**, not x2 - `ADD HL,HL` doubles and `ADD HL,BC`
  // then adds the original back (0x4D11/0x4D12), applied to both components.
  if (speed & 0x40) {
    vy *= 3;
    vx *= 3;
  }
  // 0x4D19: bit 7 is x4, two doublings per component.
  if (speed & 0x80) {
    vy *= 4;
    vx *= 4;
  }
  const count = speed & 0x3f;
  vy *= count;
  vx *= count;

  slots[base + 0x08] = vy & 0xff;
  slots[base + 0x09] = (vy >> 8) & 0xff;
  slots[base + 0x0a] = vx & 0xff;
  slots[base + 0x0b] = (vx >> 8) & 0xff;
}

/** Aim tables read by 0x4C91 (kb/data/dir_angle_thresholds, dir_remap_table). */
const DIR_ANGLE_THRESHOLDS = 0x4d42;
const DIR_REMAP_TABLE = 0x4d45;

/**
 * `player_pos_snapshot` (0x4C8B) - in truth "aim at the player": compute the
 * 16-way direction from the entity at `base` to the player and write the
 * velocity from it, scaled by the entity's speed byte (+0x17).
 *
 * Quadrant flags (0xE128): bit2 = player above, bit3 = player left,
 * bit4 = |dx| >= |dy| (axis swap). ratio = min*256/max through div_hl_e's
 * 8-bit result; three thresholds pick the octant; the 32-entry remap folds
 * octant + flags into a direction index.
 */
export function aimAtPlayer(pool, rom, base) {
  const dir = aimDirection(pool, rom, base);
  setVelocityFromDir(pool.slots, base, rom, dir, pool.slots[base + 0x17]);
  return dir;
}

/**
 * The aim-only half, `0x4C91`. Several callers want the **direction code**
 * without touching their own velocity - the base core's five-way fan
 * (0x8D98) and the veybar's dive (0x7D99) both do `CALL 0x4C91` and then
 * decide what to do with `E` themselves. Calling the 0x4C8B wrapper there
 * would additionally rewrite the shooter's velocity.
 *
 * @returns {number} the 4-bit direction code toward the player
 */
export function aimDirection(pool, rom, base) {
  const s = pool.slots;
  let flags = 0;
  let dy = s[0x01] - s[base + 0x01];
  if (dy < 0) {
    dy = -dy;
    flags |= 0x04;
  }
  if (dy === 0) dy = 1;
  let dx = s[0x02] - s[base + 0x02];
  if (dx < 0) {
    dx = -dx;
    flags |= 0x08;
  }
  if (dx === 0) dx = 1;
  let mn = dx;
  let mx = dy;
  if (dx >= dy) {
    mn = dy;
    mx = dx;
    flags |= 0x10;
  }
  const ratio = Math.round((mn * 256) / mx) & 0xff;
  let b = 3;
  let tp = DIR_ANGLE_THRESHOLDS;
  while (b > 0 && ratio >= rom.byte(tp)) {
    tp++;
    b--;
  }
  return rom.byte(DIR_REMAP_TABLE + (b | flags));
}

/** `player_ship_handler` (0x75D5): put the ship in slot 0 if it is empty. */
export function spawnPlayerShip(pool) {
  const s = pool.slots;
  const b = SLOT_PLAYER * ENTITY_STRIDE;
  if (s[b] !== 0) return;
  pool.clear(SLOT_PLAYER);
  s[b] = TYPE_PLAYER | 0x80;
  s[b + 0x01] = SHIP_SPAWN.y;
  s[b + 0x02] = SHIP_SPAWN.x;
  s[b + 0x03] = SHIP_SPAWN.satName;
  s[b + 0x04] = SHIP_SPAWN.satColor;
  s[b + 0x05] = 0x80; // invincible while the timer runs
  s[b + 0x0c] = 0x00; // motion is driven here, not by entity_update
  s[b + 0x17] = SHIP_SPEED;
  s[b + 0x1b] = SHIP_SPAWN.invincibility;
}

/**
 * The tail of `player_ship_handler` (0x75FF-0x760F), which runs on **every**
 * ship spawn, not just the first: `fire_reset`, then `0xE10B = 0` and
 * `0xE130 = 0` before reloading the shot parameters. Dying therefore costs
 * the player the whole main-shot power-up chain, not just the fire weapon.
 *
 * @param {import('../context.js').Context} ctx
 */
export function resetShipPower(ctx) {
  fireSelect(ctx.player, ctx.rom, 0, ctx); // 0x75FF fire_reset
  ctx.player.shotLevel = 0; // 0x7602
  if (ctx.spawn) ctx.spawn.encounter = 0; // 0x7606
  loadShotParams(ctx.player, ctx.rom); // 0x760F
}

/**
 * `player_ship_update` (0x7612): one frame of ship logic.
 * @param {import('../context.js').Context} ctx
 */
export function playerShipUpdate(ctx) {
  const { pool, rom, input, player } = ctx;
  const s = pool.slots;
  const b = SLOT_PLAYER * ENTITY_STRIDE;

  player.dirSelector = directionSelector(input.state);

  // 0x7616: a centred stick skips both the velocity set and the move.
  if (player.dirSelector !== DIR_CENTRED) {
    const dir = rom.byte(XVEL_TABLE + player.dirSelector);
    setVelocityFromDir(s, b, rom, dir, s[b + 0x17]);

    let y = ((s[b + 0x01] << 8) | s[b + 0x06]) + signed16(s, b, 0x09, 0x08);
    let x = ((s[b + 0x02] << 8) | s[b + 0x07]) + signed16(s, b, 0x0b, 0x0a);
    s[b + 0x01] = clamp((y >> 8) & 0xff, SHIP_Y_MIN, SHIP_Y_MAX);
    s[b + 0x06] = y & 0xff;
    s[b + 0x02] = clamp((x >> 8) & 0xff, SHIP_X_MIN, SHIP_X_MAX);
    s[b + 0x07] = x & 0xff;
  }

  updateShot(ctx);
  spawnFireWeapon(ctx); // 0x76E9

  // 0x7726: flash the sprite colour while the spawn invincibility runs.
  if (s[b + 0x05] & 0x80) {
    s[b + 0x04] ^= 0x0e;
    s[b + 0x1b] = (s[b + 0x1b] - 1) & 0xff;
    if (s[b + 0x1b] === 0) {
      s[b + 0x05] &= ~0x80;
      s[b + 0x04] = SHIP_SPAWN.satColor;
    }
  }

  pushEntitySprite(pool, SLOT_PLAYER);
}

/** Shot firing and cadence (0x767B-0x76E8). */
function updateShot(ctx) {
  const { pool, rom, input, player } = ctx;
  const s = pool.slots;
  const b = SLOT_PLAYER * ENTITY_STRIDE;

  player.fireCadence = Math.min(0xff, player.fireCadence + 1);
  if ((input.state & IN_SHOT) !== 0) {
    // 0x7682: released -> E110 = 1, so the NEXT press fires immediately.
    // This is what makes tap-firing much faster than the 20-frame hold
    // cadence - Zanac's signature rapid-fire technique.
    player.shotCooldown = 1;
    return;
  }
  if (--player.shotCooldown > 0) return;

  // 0x768F: the reload and the ALC bookkeeping happen on every expiry,
  // whether or not a shot slot turns out to be free.
  player.shotCooldown = SHOT_PERIOD;
  // 0x7691: a cadence of 0x12 frames or more is off the table entirely and
  // scores a flat advance of 1; below that the index is `cadence - 2`, so a
  // 2-frame tap lands on entry 0 - the biggest push there is.
  const cadence = player.fireCadence;
  applyFireAdvance(ctx, cadence >= 0x12 ? 1 : rom.byte(SHOT_RATE_TABLE + cadence - 2));
  player.fireCadence = 0; // 0x76B8: E13F = 0
  player.fireEvents = Math.min(0xff, player.fireEvents + 1); // 0x76BF: E141 saturating

  // 0x76C9: only (0xE10D) slots are scanned - shot level 0 allows 2 in
  // flight, upgrades alternate the cap between 2 and 3.
  const slot = pool.findFree(SHOT_SLOT_FIRST, SHOT_SLOT_FIRST + (player.shotCap || 2) - 1);
  if (slot < 0) return;

  player.shotsFired = (player.shotsFired + 1) & 0xff; // 0x76E8: E140++ on spawn only

  const sb = slot * ENTITY_STRIDE;
  pool.clear(slot);
  // 0x7228 `shot_handler`'s first frame: the SFX event is derived from the
  // shot's own sprite byte, `3 + (0xE10F >> 2)` - 13 / 14 / 15 for the one-,
  // two- and three-stream sprites, so the pew rises in pitch as the main shot
  // powers up.
  ctx.sound.playEvent(3 + (player.shotSprite >> 2));
  s[sb] = TYPE_SHOT | 0x80;
  s[sb + 0x01] = s[b + 0x01];
  s[sb + 0x02] = s[b + 0x02];
  s[sb + 0x03] = player.shotSprite;
  s[sb + 0x04] = 0x8f;
  s[sb + 0x0c] = BEH_Y_MOTION;
  // 0x7221: vy = CPL(shot speed) - i.e. negative, so the shot travels upward.
  s[sb + 0x09] = ~player.shotSpeed & 0xff;
  s[sb + 0x08] = 0;
}

/**
 * 0x76A6 — the ALC's **primary feedback loop**, and the one the port was
 * missing: the advance looked up in `shot_rate_table` is added to *two*
 * accumulators, and each carry bumps a different counter.
 *
 * - `0xE12F += adv`, carry -> `inc_encounter_a` (0xBFAB): **0xE12E++** and
 *   0xE12D bit 0, which is what re-aims the spawn table.
 * - `0xE131 += adv`, carry -> `SUB_bfc8` (0xBFC8): **0xE130++**, frozen while
 *   a base is active.
 *
 * The faster the player fires, the smaller the cadence index and the bigger
 * the advance, so aggressive play escalates the enemy mix. Computing the
 * advance and then dropping it - as the port did - pins the spawn table near
 * its start, and the round only ever sends the handful of types that never
 * shoot back.
 *
 * @param {import('../context.js').Context} ctx
 * @param {number} adv
 */
function applyFireAdvance(ctx, adv) {
  const spawn = ctx.spawn;
  if (!spawn) return;
  const lo = spawn.accLo + adv;
  spawn.accLo = lo & 0xff;
  if (lo > 0xff) {
    if (spawn.accHi < 0xff) spawn.accHi++; // inc_encounter_a
    spawn.ctrl |= 0x01;
  }
  const lo2 = spawn.accLo2 + adv;
  spawn.accLo2 = lo2 & 0xff;
  if (lo2 > 0xff) {
    // SUB_bfc8: 0xE130 is frozen while a base encounter is running.
    if (!(ctx.base && ctx.base.flags & 0x02) && spawn.encounter < 0xff) {
      spawn.encounter++;
    }
  }
}

/**
 * Run the non-player slots: each entity's type handler first (so a freshly
 * spawned one is set up on the frame it appears), then the shared update.
 */
export function updateEntities(ctx) {
  const { pool, rom, scroll } = ctx;
  for (let slot = SLOT_PLAYER + 1; slot < pool.slots.length / ENTITY_STRIDE; slot++) {
    if (!pool.active(slot)) continue;
    if (slot === FIRE_SLOT && pool.type(slot) === 0x03) {
      fireWeaponHandler(ctx);
      continue;
    }
    if (slot === FIRE_SLOT && pool.type(slot) === 19) {
      // hit last frame: death_transition_table[3] = 19 -> expire dispatch
      fireExpireHandler(ctx);
      continue;
    }
    // A false return is the `POP HL` / `RET NC` early-out in wide_struct_init:
    // the rest of the handler, including the sprite push, is skipped.
    if (!runTypeHandler(pool, slot, scroll, ctx)) continue;
    entityUpdate(pool, slot, rom);
    postTypeHandler(pool, slot); // complement sprite + child keepalive
  }
}

function signed16(slots, base, hi, lo) {
  const v = (slots[base + hi] << 8) | slots[base + lo];
  return v >= 0x8000 ? v - 0x10000 : v;
}

function clamp(v, lo, hi) {
  return v < lo ? lo : v > hi ? hi : v;
}

// --------------------------------------------------------------------------
// Fire weapon (type 3, slot 4 / 0xE380)
// --------------------------------------------------------------------------

/** `fire_init_table` (0x751F): fire_num -> [counter 0xE14D, mode 0xE14E]. */
const FIRE_INIT_TABLE = 0x751f;
/** `fire2_special_table` (0x752F): 7 x [enemy type, count, interval]. */
const FIRE2_SPECIAL_TABLE = 0x752f;
/** Fire-weapon spawn SFX (0x725E). */
const FIRE_SFX = 0x06;

/**
 * `fire_select` (0x7548): choose weapon `n` - load its counter/mode pair and
 * reset the 0x3C-frame life timer.
 *
 * `fire_reset` (0x7544) is the same routine entered one instruction earlier,
 * with `0xE14F = 0` in front of it. Since 0x7548 is only ever reached with 0
 * through that door, `n === 0` here means the reset.
 */
export function fireSelect(player, rom, n, ctx) {
  const previous = player.fireNum; // D at 0x754C, read before the store
  player.fireNum = n & 7;
  if (player.fireNum === 0) player.maxedChips = 0; // 0x7545, the `fire_reset` half
  player.fireCounter = rom.byte(FIRE_INIT_TABLE + 2 * player.fireNum);
  player.fireMode = rom.byte(FIRE_INIT_TABLE + 2 * player.fireNum + 1);
  player.fireFrame = 0x3c;
  // 0x7564: **selecting a weapon re-types the fire slot**, which is how the
  // outgoing weapon's entity is disposed of. Weapon 2 gets its shield at once
  // (type 3 with bit 7 clear, so the handler inits it next frame); any other
  // change stamps 0x28 over whatever the old weapon left in the slot, and
  // that despawns on the next dispatch. Re-selecting the same weapon leaves
  // the slot alone, so a refresh does not restart the shield.
  //
  // Without this the slot stays occupied forever after a weapon change: dying
  // with fire 3 up leaves the orbiting shield parked at the spot the ship
  // died, and because `spawn_fire_weapon` only spawns into a free slot, the
  // player never gets fire 0 back either.
  if (ctx && ctx.pool) {
    const b = FIRE_SLOT * ENTITY_STRIDE;
    if (player.fireNum === 2) ctx.pool.slots[b] = 0x03;
    else if (player.fireNum !== previous) ctx.pool.slots[b] = 0x28;
  }
  // 0x7575: taking **fire weapon 2 summons an enemy wave**. The 3-byte record
  // from `fire2_special_table` goes straight to `sub_97BC`, the same helper
  // map command 1 uses, so it becomes a type-69 emitter carrying
  // `(enemy type, count, interval)`. The row is picked by shot power level,
  // **+3 entries once the round reaches 5** - the ALC's way of charging for a
  // strong weapon.
  if (player.fireNum === 2 && ctx && ctx.pool) {
    let entry = FIRE2_SPECIAL_TABLE + 3 * (player.shotLevel & 0x0f);
    if (ctx.state && ctx.state.round >= 5) entry += 3; // 0x7589
    placeWaveRecord(ctx.pool, rom, entry);
  }
}

/**
 * The fire-spawn tail of `player_ship_update` (0x76E9): while bit 5 is held
 * and the 0xE380 slot is free, write the direction selector into the slot's
 * persistent +0x1A (0x76FD - this is how fire 0 aims along the steering
 * direction), then type 3 + the ship's position.
 */
export function spawnFireWeapon(ctx) {
  const { pool, input, player } = ctx;
  if ((input.state & 0x20) !== 0) return; // IN_FIRE, active low
  const s = pool.slots;
  const b = FIRE_SLOT * ENTITY_STRIDE;
  if (s[b] !== 0) return;
  s[b + 0x1a] = player.dirSelector; // E39A <- E10C (0x76FD)
  s[b] = 0x03;
  s[b + 0x01] = s[SLOT_PLAYER * ENTITY_STRIDE + 0x01];
  s[b + 0x02] = s[SLOT_PLAYER * ENTITY_STRIDE + 0x02];
}

/**
 * `fire_weapon_handler` (0x7253): the type-3 entity. First frame: SFX 6 and
 * the per-weapon init dispatch (0x7269); afterwards the update dispatch
 * (0x727F). All eight weapons are ported; the per-weapon constants and aim
 * paths are catalogued in kb/guides/fire-weapon-dispatch.md.
 */
export function fireWeaponHandler(ctx) {
  const { pool, rom, player } = ctx;
  const s = pool.slots;
  const b = FIRE_SLOT * ENTITY_STRIDE;

  if ((s[b] & 0x80) === 0) {
    s[b] |= 0x80;
    ctx.sound.playEvent(FIRE_SFX);
    // Common init at 0x72BC: colour 0x80 (cycled), sat/behaviour/speed from
    // per-weapon constants; C's low bit selects the aim path, whose direction
    // table differs per weapon.
    switch (player.fireNum) {
      case 0: {
        // 0x72B3: BC=0x0301, DE=0x0CC2, HL=0x7758 (xvel_table).
        commonFireInit(s, b, 0x0c, 0x03, 0xc2);
        const dir = rom.byte(0x7758 + s[b + 0x1a]);
        setVelocityFromDir(s, b, rom, dir, s[b + 0x17]);
        break;
      }
      case 1:
        // 0x72A8: fire_dec_ammo; BC=0x0100, DE=0x08FE - straight up at 2px/f.
        decFireAmmo(ctx);
        commonFireInit(s, b, 0x08, 0x01, 0xfe);
        s[b + 0x09] = 0xfe; // vy = -2
        break;
      case 2:
        // 0x729D: BC=0x0000, DE=0x2400 - the ship-following shield.
        commonFireInit(s, b, 0x24, 0x00, 0x00);
        break;
      case 3:
        // 0x7331: the orbiting shield - manual motion via rotating direction.
        s[b + 0x03] = 0x10;
        s[b + 0x04] = 0x8f;
        s[b + 0x0c] = 0x00;
        s[b + 0x0f] = 0x00; // rel-X accumulator (lo)
        s[b + 0x10] = 0xf6; // rel-X (hi)
        s[b + 0x0d] = 0x00; // rel-Y accumulator (lo)
        s[b + 0x0e] = 0xc0; // rel-Y (hi)
        s[b + 0x17] = 0xc3; // x8 prescale, 3 steps
        s[b + 0x11] = 0x01; // step countdown
        s[b + 0x12] = 0xff; // rotating direction index
        break;
      case 7: {
        // 0x728F: fire_life_timer; BC=0x0301, DE=0x08C3, HL=0x7321 - the
        // angled shot. NOTE the table: 0x7321 ("fire0_dir_table" in the KB)
        // belongs to fire 7; fire 0 aims through xvel_table (0x7758).
        tickFireLifeTimer(ctx);
        commonFireInit(s, b, 0x08, 0x03, 0xc3);
        const dir = rom.byte(0x7321 + s[b + 0x1a]);
        setVelocityFromDir(s, b, rom, dir, s[b + 0x17]);
        break;
      }
      case 4:
      case 5:
      case 6: {
        // Shared init at 0x73D2: white, vy=-2, Y-motion, one ammo per spawn.
        decFireAmmo(ctx);
        s[b + 0x03] = player.fireNum === 5 ? 0x0c : 0x10;
        s[b + 0x04] = 0x8f;
        s[b + 0x08] = 0x00;
        s[b + 0x09] = 0xfe;
        s[b + 0x0c] = 0x01;
        if (player.fireNum === 4) {
          // 0x73F1: the horizontal pendulum. Target X = own X clamped to
          // [0x50,0xA0]; starts 0x18 to the right with vx = -12 and a +4/256
          // per-frame pull back toward the target; 0x46 frames later the
          // vertical rise stops (behaviour -> X only).
          s[b + 0x03] = 0x24;
          s[b + 0x09] = 0xff;
          s[b + 0x0c] = 0x03;
          let tx = s[b + 0x02];
          if (tx < 0x50) tx = 0x50;
          else if (tx >= 0xa1) tx = 0xa0;
          s[b + 0x14] = tx;
          s[b + 0x02] = (tx + 0x18) & 0xff;
          if (s[b + 0x01] < 0x50) s[b + 0x01] = 0x50;
          s[b + 0x0a] = 0x00;
          s[b + 0x0b] = 0xf4; // vx = -12
          s[b + 0x0f] = 0x00; // accel accumulator lo
          s[b + 0x10] = 0x04; // accel = +0x0400 per frame
          s[b + 0x1c] = 0x46;
          s[b + 0x1b] = 0x3c;
        }
        break;
      }
      default:
        pool.clear(FIRE_SLOT);
        return;
    }
  }

  switch (player.fireNum) {
    case 2: {
      // 0x72F5: pin to the ship, 8px above.
      s[b + 0x01] = (s[SLOT_PLAYER * ENTITY_STRIDE + 0x01] - 8) & 0xff;
      s[b + 0x02] = s[SLOT_PLAYER * ENTITY_STRIDE + 0x02];
      break;
    }
    case 3: {
      // 0x735D: rotate the direction each frame, integrate a relative
      // position, then pin it to the (clamped) player position - the orbit.
      s[b + 0x11] = (s[b + 0x11] - 1) & 0xff;
      if (s[b + 0x11] === 0) {
        s[b + 0x11] = 0x01;
        s[b + 0x12] = (s[b + 0x12] + 1) & 0xff;
        setVelocityFromDir(s, b, rom, s[b + 0x12] & 0x0f, s[b + 0x17]);
      }
      let rel = ((s[b + 0x0e] << 8) | s[b + 0x0d]) + signed16(s, b, 0x09, 0x08);
      s[b + 0x0d] = rel & 0xff;
      s[b + 0x0e] = (rel >> 8) & 0xff;
      const py = clamp(s[SLOT_PLAYER * ENTITY_STRIDE + 0x01], 0x38, 0xa7);
      s[b + 0x01] = (py + ((rel >> 8) & 0xff)) & 0xff;
      rel = ((s[b + 0x10] << 8) | s[b + 0x0f]) + signed16(s, b, 0x0b, 0x0a);
      s[b + 0x0f] = rel & 0xff;
      s[b + 0x10] = (rel >> 8) & 0xff;
      const px = clamp(s[SLOT_PLAYER * ENTITY_STRIDE + 0x02], 0x48, 0xa7);
      s[b + 0x02] = (px + ((rel >> 8) & 0xff)) & 0xff;
      tickFireLifeTimer(ctx);
      pushEntitySprite(pool, FIRE_SLOT);
      return; // manual motion: no entity_update
    }
    case 4: {
      // 0x7439: accelerate vx toward the target, flipping past it - the
      // pendulum. When the rise countdown ends, drop the Y motion.
      let vx = ((s[b + 0x0b] << 8) | s[b + 0x0a]) + ((s[b + 0x10] << 8) | s[b + 0x0f]);
      if (s[b + 0x02] >= s[b + 0x14]) vx -= 2 * ((s[b + 0x10] << 8) | s[b + 0x0f]);
      s[b + 0x0a] = vx & 0xff;
      s[b + 0x0b] = (vx >> 8) & 0xff;
      s[b + 0x1c] = (s[b + 0x1c] - 1) & 0xff;
      if (s[b + 0x1c] === 0) s[b + 0x0c] = 0x02;
      break;
    }
    case 5: {
      // 0x7464: a lob - X pinned to the ship, upward speed decaying +4/256
      // per frame; once it falls back past shipY+16 it vanishes.
      if (s[b + 0x01] < 0x10) s[b + 0x01] = 0x10;
      s[b + 0x02] = s[SLOT_PLAYER * ENTITY_STRIDE + 0x02];
      if (((s[SLOT_PLAYER * ENTITY_STRIDE + 0x01] + 0x10) & 0xff) < s[b + 0x01]) {
        pool.clear(FIRE_SLOT);
        if (player.fireCounter === 0) fireSelect(player, rom, 0, ctx);
        return;
      }
      let vy = ((s[b + 0x09] << 8) | s[b + 0x08]) + 4;
      s[b + 0x08] = vy & 0xff;
      s[b + 0x09] = (vy >> 8) & 0xff;
      break;
    }
    case 7:
      tickFireLifeTimer(ctx); // 0x7306
      break;
    default:
      break;
  }

  // Shared update tail (0x72DE): cycle the sprite colour, entity_update.
  s[b + 0x04] = (s[b + 0x04] + 1) & 0x8f;
  entityUpdate(pool, FIRE_SLOT, rom);

  // 0x72EA epilogue (fires 1/2): once the projectile despawns, an exhausted
  // counter drops the weapon back to fire 0.
  if (!pool.active(FIRE_SLOT) && player.fireNum !== 0 && player.fireCounter === 0) {
    fireSelect(player, rom, 0, ctx); // fire_reset (0x7544)
  }
}

/** The shared block at 0x72BC (colour is always 0x80, cycled per frame). */
function commonFireInit(s, b, satName, behaviour, speed) {
  s[b + 0x04] = 0x80;
  s[b + 0x03] = satName;
  s[b + 0x0c] = behaviour;
  s[b + 0x17] = speed;
  s[b + 0x08] = 0x00;
  s[b + 0x09] = speed; // overwritten when the aim path runs
}

/** `fire_dec_ammo` (0x732A): one shot of ammo per spawn. */
function decFireAmmo(ctx) {
  if (ctx.player.fireCounter > 0) ctx.player.fireCounter--;
}

/**
 * `fire_life_timer` (0x730B): every 0x3C frames burn one unit of the
 * counter; on wrap the weapon resets to fire 0.
 */
function tickFireLifeTimer(ctx) {
  const player = ctx.player;
  player.fireFrame = (player.fireFrame - 1) & 0xff;
  if (player.fireFrame !== 0) return;
  player.fireFrame = 0x3c;
  player.fireCounter--;
  if (player.fireCounter < 0) {
    fireSelect(player, ctx.rom, 0, ctx);
    ctx.pool.clear(FIRE_SLOT);
  }
}

/**
 * `update_fire_display` (0x7594): the FIRE readout in the status panel -
 * "FIRE " plus the weapon number at 0x3A59, and the 0xE14D ammo counter at
 * 0x3A7A (blank while fire 0 is selected, per 0x75B7).
 */
export function updateFireDisplay(screen, player) {
  screen.writeNameTable(0x3a59, 'FIRE ');
  screen.writeNameTable(0x3a5e, [0x30 + player.fireNum]); // 0x75A6: (0xE14B)
  // 0x75B7: with **fire 0 selected the ammo line is blank** - 0x75C9 prints
  // an inline run of spaces. Only an actual weapon shows its 0xE14D counter.
  if (player.fireNum === 0) {
    screen.writeNameTable(0x3a7a, [0x20, 0x20, 0x20, 0x20]);
    return;
  }
  const v = player.fireCounter;
  screen.writeNameTable(0x3a7a, [
    v >= 100 ? 0x30 + ((v / 100) | 0) : 0x20,
    v >= 10 ? 0x30 + (((v / 10) | 0) % 10) : 0x20,
    0x30 + (v % 10),
  ]);
}

/**
 * The fire-expire dispatch (0x74A4), reached when the fire entity is hit:
 * `collision_response` remaps type 3 -> 19, and type 19's handler restores
 * 0x83 and dispatches per weapon (table 0x74AE). This is where the shields'
 * durability lives.
 */
export function fireExpireHandler(ctx) {
  const { pool, rom, player } = ctx;
  const s = pool.slots;
  const b = FIRE_SLOT * ENTITY_STRIDE;
  s[b] = 0x83; // 0x74A4: back to an active fire entity

  switch (player.fireNum) {
    case 0: // 0x74BE: fire 0 simply dies
      pool.clear(FIRE_SLOT);
      break;
    case 2: // 0x74C1: the following shield burns durability per hit
      ctx.sound.playEvent(0x18);
      player.fireCounter--;
      if (player.fireCounter < 0) {
        fireSelect(player, rom, 0, ctx);
        pool.clear(FIRE_SLOT);
        break;
      }
      if (player.fireCounter === 0x14) s[b + 0x03] = 0x20; // shrink at 20 left
      break;
    case 4: // 0x74E2: a personal 0x3C-hit pool (+0x1B) with visual decay
      ctx.sound.playEvent(0x18);
      s[b + 0x1b] = (s[b + 0x1b] - 1) & 0xff;
      if (s[b + 0x1b] === 0) {
        pool.clear(FIRE_SLOT);
        if (player.fireCounter === 0) fireSelect(player, rom, 0, ctx);
      } else if (s[b + 0x1b] === 0x1e) s[b + 0x03] = 0x20;
      else if (s[b + 0x1b] === 0x0f) s[b + 0x04] = 0x81;
      break;
    case 6: // 0x7511: the nuke - taking a hit explodes every enemy on screen
      explodeEnemies(ctx);
      ctx.sound.playEvent(0x13);
      pool.clear(FIRE_SLOT);
      if (player.fireCounter === 0) fireSelect(player, rom, 0, ctx);
      break;
    default:
      // fires 1/3/5/7 shrug the hit off (0x72EA / 0x735D / 0x7464 / 0x7306)
      break;
  }
}

/**
 * `explode_enemies` (0x8A26): every live enemy in the pool becomes the type-35
 * death explosion, keeping its own type in +0x18 for the score award.
 */
function explodeEnemies(ctx) {
  const { pool } = ctx;
  const s = pool.slots;
  for (let slot = 5; slot <= 25; slot++) {
    const type = pool.type(slot);
    if (type === 0 || type === 39 || PICKUP_TYPES_LOCAL.has(type)) continue;
    const b = slot * ENTITY_STRIDE;
    s[b + 0x18] = type;
    s[b] = 35;
  }
}
const PICKUP_TYPES_LOCAL = new Set([63, 83]);
