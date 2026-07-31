/**
 * Entity type handlers (subsystem G).
 *
 * Only the wide ground structures are ported so far. `entity_jump_table`
 * routes types 70-71, 81-82 and 87-89 to a single handler at 0x87AB, which is
 * what the round-1 greeble streams spawn (observed live: 0x46, 0x4B, 0x52,
 * 0x57, 0x58).
 *
 * These entities deliberately carry **no visible sprite** - `entity_table`
 * records type 82 with sat_colour 0x00, i.e. transparent. The structure the
 * player sees is drawn by the tile layer; the entity exists to own a hitbox and
 * to occupy its column for `check_col_clear`. What it does need is a correct
 * `sat_name`, because that byte indexes `collision_size_table`.
 */

import { ENTITY_STRIDE } from './entity.js';
import { addScore } from './hud.js';
import {
  aimAtPlayer,
  aimDirection,
  setVelocityFromDir,
  loadShotParams,
  fireSelect,
} from './player.js';
import { hitbox, hitboxOverlaps, checkEntityCollisions, collisionResponse } from './collision.js';
import { BASE_SEGMENT_TYPES } from './base.js';
import { runBaseSegment } from './base_segment.js';

/** Types the 0x87AB wide-structure handler owns. */
const WIDE_STRUCTURE_TYPES = new Set([70, 71, 81, 82, 84, 85, 86, 87, 88, 89]);
/**
 * Types 84-86 have their own prologue (`handler_type84_wide_variant`, 0x8EB7)
 * that joins the shared body at **0x87C3** rather than 0x87B0 - so they skip
 * the idol-table load entirely and instead arm a firing countdown. They are
 * the only wide structures that shoot.
 */
const WIDE_GUN_TYPES = new Set([84, 85, 86]);

/**
 * Init values for a wide ground structure, from `entity_table`'s type-82
 * column (live capture, sprint 0021).
 */
const WIDE_STRUCTURE_INIT = {
  satName: 0x24,
  satColor: 0x00, // transparent: the tile layer draws the structure
  behaviour: 0x00, // stationary; the map scrolls past it
  field19: 0x04,
  childHi: 0x01,
  colWidth: 0x07,
};

/** Type-byte bit 7: the structure has entered the screen and is running. */
const ON_SCREEN = 0x80;
/** Rows advance a structure by one tile (0x8F35 / 0x8F4F). */
const SCROLL_STEP = 8;
/** Extra nudge applied on the frame a structure enters (0x8F3F). */
const ENTRY_NUDGE = 0x10;
/** Past this Y the structure has left the bottom of the playfield (0x8F54). */
const DESPAWN_Y = 0xd0;
/** `scroll_state` flag bit 1 - set once a map row was built this frame. */
const SCROLLED = 0x02;

/**
 * `wide_struct_init` (0x8F25), the prologue every 0x87AB structure runs.
 *
 * A placed structure starts **below the screen** - the placement records put Y
 * around 240 - and is advanced 8 pixels per scroll step. It is not on screen
 * until that 8-bit addition *wraps past 255*, at which point bit 7 of the type
 * byte is set and Y is nudged a further 16, so the structure enters from the
 * top. Once running, the same 8-pixel step carries it down until Y reaches
 * 0xD0 and it despawns.
 *
 * Both branches are gated on `scroll_state` bit 1, so structures move in step
 * with the terrain rather than per frame. The `POP HL` at 0x8F2B is what lets
 * the not-yet-entered path skip the rest of the entity handler entirely: it
 * discards the handler's return address so the following `RET NC` unwinds one
 * level further than usual.
 *
 * @param {import('./entity.js').EntityPool} pool
 * @param {number} slot
 * @param {import('./scroll.js').ScrollState} scroll
 * @returns {boolean} false when this frame's handler body should be skipped
 */
export function runTypeHandler(pool, slot, scroll, ctx) {
  const s = pool.slots;
  const b = slot * ENTITY_STRIDE;
  const type = s[b] & 0x7f;
  // Type 0x28's handler is `JP entity_clear` (0x852C) - an instant despawn
  // with no animation. It is how the game retires an entity from outside its
  // own handler: `reset_entities` stamps it over the pool at a round change,
  // and `fire_select` stamps it over the fire slot when the weapon changes.
  if (type === TYPE_DESPAWN) {
    pool.clear(slot);
    return false;
  }
  if (type === TYPE_DEATH_EXPLOSION) return runDeathExplosion(pool, slot, ctx, false);
  if (type === TYPE_BASE_DAMAGE) return runBaseDamage(pool, slot, scroll, ctx);
  if (type === TYPE_PROTO_STRUCTURE && (s[b] & 0x80) === 0) {
    s[b] = TYPE_GROUND_STRUCTURE; // 0x8279 self-transforms before doing anything
    return true;
  }
  if (type === TYPE_MAIN_ATTACKER) return runType44(pool, slot, ctx);
  if (type >= 12 && type <= 15) return runTeruzo(pool, slot, ctx);
  if (type === 68 && ctx) return runProtoBox(pool, slot, ctx);
  if (type >= 4 && type <= 6 && ctx) return runBox(pool, slot, ctx);
  if ((type === 7 || type === 8 || type === 9) && ctx) return runUmber(pool, slot, ctx);
  if (type >= 16 && type <= 18 && ctx) return runLuster(pool, slot, ctx);
  if (type === 37) return runLeadBullet(pool, slot, ctx, true);
  if (type === 38) return runLeadBullet(pool, slot, ctx, false);
  if (type === 61) return runLargeDescender(pool, slot, ctx);
  if (type === 11 || type === 69) return runWaveSpawner(pool, slot, ctx);
  if (type >= 22 && type <= 25) return runVeybar(pool, slot, ctx, type);
  if (type >= 26 && type <= 29) return runEdgeSwooper(pool, slot, ctx, type);
  if (type >= 46 && type <= 55) return runGroundGun(pool, slot, ctx, type);
  if (type === 10) return runDuster(pool, slot, ctx);
  if (type === 20) return runLeadHoming(pool, slot, ctx);
  if (type === 21) return runLightBar(pool, slot, ctx);
  if (type >= 56 && type <= 59) return runDescenderDart(pool, slot, ctx, type);
  if (type === 41) return runCurvingShot(pool, slot, ctx);
  if (type === 36) return runFlashing(pool, slot, ctx);
  if (type === 64) return runProtoStructure(pool, slot, ctx);
  if (type === 30 || type === 32) return runStealthPair(pool, slot, ctx, type);
  if (type === 31 || type === 33) return runStealthTracker(pool, slot, ctx);
  if (type === 34 || type === 65 || type === 66) return runBurster(pool, slot, ctx, type);
  if (type === 67) return runPhaseCharger(pool, slot, ctx);
  if (type === 62) return runOneUp(pool, slot, ctx);
  if (type === 42 || type === 43 || type === 45)
    return runBaseProjectile(pool, slot, ctx, type);
  if (BASE_SEGMENT_TYPES.has(type)) return runBaseSegment(pool, slot, ctx, type);
  if (type === 72) return runOrb(pool, slot, ctx);
  if (type === TYPE_POWER_CHIP) return runPowerChip(pool, slot, ctx);
  if (type === TYPE_FIRE_UPGRADE) return runBlackShadow(pool, slot, ctx);
  if (type === TYPE_COL_MARKER) {
    // 0x8525: pure keepalive - decrement +0x18, clear at 0, draw nothing.
    s[b + 0x18] = (s[b + 0x18] - 1) & 0xff;
    if (s[b + 0x18] === 0) pool.clear(slot);
    return false;
  }
  const air = AIRBORNE_INIT.get(type);
  if (air) {
    if ((s[b] & 0x80) === 0) {
      s[b] |= 0x80;
      initAirborne(s, b, air);
    }
    return true;
  }
  if (!WIDE_STRUCTURE_TYPES.has(s[b] & 0x7f)) return true; // other types: leave as-is

  const scrolled = (scroll.flags & SCROLLED) !== 0;

  if ((s[b] & ON_SCREEN) === 0) {
    if (!scrolled) return false;
    const y = s[b + 0x01] + SCROLL_STEP;
    s[b + 0x01] = y & 0xff;
    if (y <= 0xff) return false; // still below the bottom edge
    s[b] |= ON_SCREEN;
    s[b + 0x01] = (s[b + 0x01] + ENTRY_NUDGE) & 0xff;
    const idolIdx = s[b + 0x03]; // the 0xE71D cursor place_tile_group stored
    const isGun = WIDE_GUN_TYPES.has(s[b] & 0x7f);
    initWideStructure(s, b); // (overwrites +0x03 with the sprite name)
    // ---- 0x87B0 body: idol-table load, HP, and the fire-box digit ----
    if (ctx) {
      const idol = ctx.scroll.idolTablePtr;
      if (isGun) {
        // 0x8EBC: no idol data - +0x1C/+0x1D are the firing countdown and
        // its reload, and the entity joins the shared body at 0x87C3.
        s[b + 0x1c] = 0x03;
        s[b + 0x1d] = 0x18;
      } else if (idol) {
        s[b + 0x1c] = ctx.rom.byte(idol + idolIdx);
        s[b + 0x1d] = ctx.rom.byte(idol + idolIdx + 1);
      }
      const active = s[b];
      s[b + 0x19] = active < 0xc8 ? 6 : active < 0xd7 ? 4 : 3; // HP by type
      if (active === 0xd2) {
        // 0x87E2: the weapon digit, written INTO THE RING as well as VRAM -
        // that is why it scrolls with the terrain in the original.
        const col = (s[b + 0x02] - 0x28) >> 3;
        const row = (s[b + 0x01] - 0x10) >> 3;
        const digit = 0x30 + (s[b + 0x1c] & 0x0f);
        if (col >= 0 && col < 24 && row >= 0 && row < 24) {
          const ringAt =
            ((ctx.scroll.ringRow + row) % 24) * 24 + col;
          ctx.scroll.ring[ringAt] = digit;
          ctx.screen.nameTable[row * 32 + col] = digit;
        }
      }
    }
    return true;
  }

  // 0x8EC7: the three gun variants fire on a countdown before they collide.
  if (ctx && WIDE_GUN_TYPES.has(s[b] & 0x7f)) fireWideGun(pool, s, b, ctx);

  // ---- active: soak shots through the 0x87CA hit points ----
  // Ground structures enter collision through the ALT entry 0x44CA (0x8806),
  // which runs the SHOTS-ONLY dispatcher (0x44F9) - the ship flies over them
  // and never dies on contact. Only airborne enemies/boxes use the full
  // 0x44BA path with the player check.
  if (ctx) {
    const hit = checkEntityCollisions(pool, ctx.rom, slot, ctx.player.fireMode, true);
    if (hit) {
      if (hit.hitBy === 0) {
        // player overlap: ignored, per 0x44CA
      } else {
      pool.clear(hit.hitBy);
      s[b + 0x19]--;
      if (s[b + 0x19] === 0) {
        // ---- destruction sub-type dispatch (0x880D): every ground
        // object carries its own bonus. Note the explosion (0x50) paths do
        // NOT score - only the shadow (0x8874) and orb (0x8833) paths call
        // add_score_for_subtype.
        const was = s[b] & 0x7f;
        s[b + 0x18] = was;
        if (was === 82 || was >= 0x59) {
          // 0x8874: fire box -> black shadow carrying +0x1C; the >= 0x59
          // wildcard (0x88A2) rolls a RANDOM fire number into +0x1C first.
          // Both leave the 4x4 crater at (X-0x28, Y-0x18).
          if (was >= 0x59) s[b + 0x1c] = (Math.random() * 256) & 0x07;
          addScore(ctx.state, ctx.rom, ctx.rom.byte(0x4b29 + was), ctx);
          ctx.sound.playEvent(0x12);
          stampCrater(ctx, 0x88d8, s[b + 0x02] - 0x28, s[b + 0x01] - 0x18);
          s[b] = 83;
          s[b + 0x05] = 0;
          s[b + 0x0c] = 0;
          return false;
        }
        if (was === 0x51) {
          // 0x8824: pedestal -> 2x3 crater + explosion
          stampCrater(ctx, 0x88c2, s[b + 0x02] - 0x24, s[b + 0x01] - 0x10);
          s[b] = 80;
          return false;
        }
        if (was >= 0x54 && was <= 0x56) {
          // 0x8854: per-subtype crater from the word table at 0x88AB
          const strip = ctx.rom.word(0x88ab + (was - 0x54) * 2);
          stampCrater(ctx, strip, s[b + 0x02] - 0x20, s[b + 0x01] - 0x10);
          s[b] = 80;
          return false;
        }
        if (was === 0x57 || was === 0x58) {
          // 0x8892: 2x2 crater (0x88B1) for 0x57, the 0x88CB strip for 0x58
          stampCrater(ctx, was === 0x57 ? 0x88b1 : 0x88cb, s[b + 0x02] - 0x20, s[b + 0x01] - 0x10);
          s[b] = 80;
          return false;
        }
        if (was < 0x51) {
          // 0x8833: totems and friends release the ORB - the slot
          // itself becomes type 72 (0x8810), keeping the idol data
          // in +0x1C/1D, and a type-81 pedestal is left behind.
          addScore(ctx.state, ctx.rom, ctx.rom.byte(0x4b29 + was), ctx);
          const ped = pool.allocEntitySlot();
          if (ped >= 0) {
            pool.clear(ped);
            const pb = ped * ENTITY_STRIDE;
            s[pb] = 0xd1; // type 81, already active
            s[pb + 0x01] = s[b + 0x01];
            s[pb + 0x02] = s[b + 0x02];
            s[pb + 0x03] = 0x24;
            s[pb + 0x19] = 0x00;
          }
          s[b] = 72; // the orb rises from the wreck
          s[b + 0x1f] = was; // 0x89B1: subtype decides the black-phase fate
          s[b + 0x05] = 0;
          s[b + 0x0c] = 0;
          return false;
        }
        s[b] = 80; // 81 / 84-86 / 87+: base-damage explosion + score
        return false;
      }
      }
    }
  }
  if (!scrolled) return true;
  const y = (s[b + 0x01] + SCROLL_STEP) & 0xff;
  s[b + 0x01] = y;
  if (y >= DESPAWN_Y) {
    pool.clear(slot);
    // 0x8F58 calls **`inc_encounter_a` (0xBFAB)** - it bumps **0xE12E**, the
    // spawn-table position, not the 0xE130 encounter counter. Every greeble
    // that scrolls off the bottom nudges the difficulty up, which is the
    // ALC's main passive source; routing it to 0xE130 by mistake pins the
    // table near its start and the round never reaches the enemies that
    // shoot back.
    if (ctx && ctx.spawn) {
      if (ctx.spawn.accHi < 0xff) ctx.spawn.accHi++;
      ctx.spawn.ctrl |= 0x01;
    }
    return false;
  }
  return true;
}

/**
 * Type 35, the entity almost everything becomes on death (0x8446).
 *
 * Despite the KB's `handler_type35_projectile` name, this is the enemy **death
 * explosion**: it awards score from the pre-hit type, runs a six-frame
 * animation, and clears itself when the frame counter wraps to 0.
 *
 * Init (0x8446 with type bit 7 clear):
 *   - feed the ALC spawn accumulators 0xE12F / 0xE131, weighting by how few
 *     shots the kill took (`0x24 - 4 * fireEvents`), then zero those counters
 *   - `add_score_for_subtype` (0x4A6A), indexed by +0x18 - the pre-hit type
 *     `collision_response` stashed
 *   - behaviour bit 2 (animate), tick 1, rate 4, frame 1, max 6,
 *     table 0x84D1
 *   - SFX event 17
 */
/** 0x28: the no-animation despawn, handler 0x852C = `JP entity_clear`. */
const TYPE_DESPAWN = 40;
const TYPE_DEATH_EXPLOSION = 35;
const EXPLOSION_ANIM_TABLE = 0x84d1;
const EXPLOSION_SFX = 0x11;
/** Structures explode with event 18 instead (0x8E1D). */
const STRUCTURE_EXPLOSION_SFX = 0x12;
/** `death_transition_table` sends every real ground structure here. */
const TYPE_BASE_DAMAGE = 80;
/** `structure_award_index_table` base, as indexed at 0x4A6F. */
const STRUCTURE_AWARD_INDEX_TABLE = 0x4b29;

function runDeathExplosion(pool, slot, ctx, isStructure) {
  const s = pool.slots;
  const b = slot * ENTITY_STRIDE;

  if ((s[b] & 0x80) === 0) {
    s[b] |= 0x80;
    s[b + 0x0c] = 0x00; // 0x8E26 clears the behaviour flags before 0x849C

    if (ctx) {
      const player = ctx.player;
      // 0x8473: the fewer shots the kill took, the bigger the difficulty nudge.
      // The structure path (0x8E1A) calls dec_encounter_a instead.
      const weighted = player.fireEvents >= 8 ? 1 : 0x24 - 4 * player.fireEvents;
      if (!isStructure) ctx.state.alcNudge = (ctx.state.alcNudge + weighted) & 0xff;
      player.fireEvents = 0;
      player.shotsFired = 0;
      // 0x849C add_score_for_subtype: +0x18 holds the type that was destroyed,
      // which indexes structure_award_index_table -> score_award_table.
      const award = ctx.rom.byte(STRUCTURE_AWARD_INDEX_TABLE + s[b + 0x18]);
      ctx.state.pendingAward = award;
      addScore(ctx.state, ctx.rom, award, ctx);
      ctx.sound.playEvent(isStructure ? STRUCTURE_EXPLOSION_SFX : EXPLOSION_SFX);
      // 0x84BC: every 16th kill raises the immediate type-44 trigger (0xE125).
      if (ctx.spawn) {
        ctx.spawn.killCounter = (ctx.spawn.killCounter - 1) & 0xff;
        if (ctx.spawn.killCounter === 0) {
          ctx.spawn.killCounter = 0x10;
          ctx.spawn.immediate = true;
        }
      }
    }

    s[b + 0x0c] |= 0x04; // animate
    s[b + 0x0d] = 0x01;
    s[b + 0x0e] = 0x04;
    s[b + 0x0f] = 0x01;
    s[b + 0x10] = 0x06;
    s[b + 0x11] = EXPLOSION_ANIM_TABLE & 0xff;
    s[b + 0x12] = EXPLOSION_ANIM_TABLE >> 8;
  }

  // 0x84C9: frame 0 means the six-step cycle wrapped - the explosion is over.
  if (s[b + 0x0f] === 0) {
    pool.clear(slot);
    return false;
  }
  return true;
}

/**
 * `handler_type80_base_damage` (0x8E14): what a ground structure becomes when
 * it is destroyed.
 *
 * It is the same explosion as type 35 - 0x8E2A is a `JP 0x849C`, straight into
 * that handler's score-and-animate setup - with three differences: it calls
 * `dec_encounter_a` (0xBFB3) rather than feeding the ALC accumulators, it plays
 * **event 18** instead of 17, and its running branch enters `wide_struct_init`
 * at 0x8F45 so the wreck keeps scrolling with the terrain while it burns.
 */
function runBaseDamage(pool, slot, scroll, ctx) {
  const s = pool.slots;
  const b = slot * ENTITY_STRIDE;
  const firstFrame = (s[b] & 0x80) === 0;

  // 0x8E1A dec_encounter_a on the frame the structure dies.
  if (firstFrame && ctx && ctx.spawn) {
    if (ctx.spawn.accHi > 0) ctx.spawn.accHi--;
    ctx.spawn.ctrl |= 0x01;
  }
  if (!runDeathExplosion(pool, slot, ctx, true)) return false;

  // 0x8E2D: on later frames the wreck rides the scroll like any structure.
  if (!firstFrame && (scroll.flags & SCROLLED) !== 0) {
    const y = (s[b + 0x01] + SCROLL_STEP) & 0xff;
    s[b + 0x01] = y;
    if (y >= DESPAWN_Y) {
      pool.clear(slot);
      return false;
    }
  }
  return true;
}


/**
 * Airborne enemy spawn data, from kb/guides/entity-sprite-mapping.md rows
 * marked `confirmed`. Each entry is what the type's handler writes on its first
 * dispatch; the shared `entity_update` then drives it from `behaviour`.
 *
 * vy/vx are the integer velocity bytes (+0x09 / +0x0B), signed.
 */
const AIRBORNE_INIT = new Map([
  // The 0x7B07 "teruzo" types 12-15 are NOT here: see the note below.
  //
  [10, { satName: 0x58, satColor: 0x89, y: 32, x: 120, vy: +2, vx: 0, behaviour: 0x01 }],
]);

/** Type 64 rewrites itself to type 44 on init (0x8279). */
const TYPE_PROTO_STRUCTURE = 64;
const TYPE_GROUND_STRUCTURE = 44;

/** Set up a freshly spawned airborne enemy. */
function initAirborne(s, b, spec) {
  s[b + 0x01] = spec.y;
  s[b + 0x02] = spec.x;
  s[b + 0x03] = spec.satName;
  s[b + 0x04] = spec.satColor;
  s[b + 0x09] = spec.vy & 0xff;
  s[b + 0x0b] = spec.vx & 0xff;
  s[b + 0x0c] = spec.behaviour;
}

/**
 * PRNG stand-in. The ROM's `prng_next` (0x43C0) mixes the R refresh register,
 * so its stream is timing-dependent and inherently unreproducible; a seeded
 * xorshift keeps headless runs deterministic instead.
 */
let prngState = 0x2a53;
function prng() {
  prngState ^= (prngState << 7) & 0xffff;
  prngState ^= prngState >> 9;
  prngState ^= (prngState << 8) & 0xffff;
  return prngState;
}

/** `random_x_pos` (0x71C5): X in [0x28,0xC6] from two PRNG fields, Y = 0. */
function randomXPos(s, b) {
  const r = prng();
  s[b + 0x02] = (((r >> 8) & 0x7f) + (r & 0x1f) + 0x28) & 0xff;
  s[b + 0x01] = 0;
}

/**
 * Teruzo (types 12-15, handler 0x7B07): a path-following enemy.
 *
 * Not a velocity enemy at all - the init masks the type's low bit away
 * (`AND 0xFE` at 0x7B13) and adds a **random** bit, so which corner a teruzo
 * enters from is `(type & 0xFE) + (R & 1)`, indexing the pointer table at
 * 0x7B63 (live entries 0x7B7B-0x7B82 -> blocks 0x7B83/0x7B98/0x7BAE/0x7BCC).
 * Each block is `[Y][X][colour]` then a 16-direction script; one direction is
 * applied every 8 frames through set_velocity_from_dir at speed 4, and a byte
 * with bit 7 set holds its low nibble forever (sending the teruzo off-screen).
 * See kb/data/teruzo_motion_tables.md - which had this right all along; the
 * fixed "vx=+1 rightward" rows in entity-sprite-mapping were the misreading.
 */
const TERUZO_PTR_BASE = 0x7b63;
const TERUZO_COMPLEMENT = 0x64;

function runTeruzo(pool, slot, ctx) {
  const s = pool.slots;
  const b = slot * ENTITY_STRIDE;
  const rom = ctx ? ctx.rom : null;
  if (!rom) return false;

  if ((s[b] & 0x80) === 0) {
    const child = pool.allocEntitySlot();
    if (child < 0) {
      pool.clear(slot);
      return false;
    }
    pool.clear(child);
    const cb = child * ENTITY_STRIDE;
    s[cb] = TYPE_COL_MARKER;
    s[cb + 0x03] = TERUZO_COMPLEMENT;
    s[cb + 0x04] = 0x81;
    s[cb + 0x18] = 2;
    s[b + 0x1b] = child;

    const index = (s[b] & 0xfe) + (prng() & 1);
    let de = rom.word(TERUZO_PTR_BASE + index * 2);
    s[b + 0x01] = rom.byte(de++);
    s[b + 0x02] = rom.byte(de++);
    s[b + 0x04] = rom.byte(de++);
    s[b + 0x1d] = de & 0xff; // direction-script cursor (persistent pair)
    s[b + 0x1e] = de >> 8;
    s[b + 0x1f] = 0x01; // step countdown: first fetch on the next frame
    s[b + 0x18] = 0x00; // script index
    s[b + 0x17] = 0x04; // speed for set_velocity_from_dir
    s[b + 0x0c] = 0x03;
    s[b + 0x03] = 0x60;
    s[b] |= 0x80;
  }

  // 0x7B55: every 8th frame fetch the next direction from the script.
  s[b + 0x1f] = (s[b + 0x1f] - 1) & 0xff;
  if (s[b + 0x1f] === 0) {
    s[b + 0x1f] = 0x08;
    const script = s[b + 0x1d] | (s[b + 0x1e] << 8);
    const step = rom.byte(script + s[b + 0x18]);
    if ((step & 0x80) === 0) s[b + 0x18] = (s[b + 0x18] + 1) & 0xff;
    setVelocityFromDir(s, b, rom, step & 0x0f, s[b + 0x17]);
  }
  return true;
}

/**
 * Pickups: the power chip (63, handler 0x78AF) and the fire-upgrade "black
 * shadow" (83, handler 0x8E3A).
 *
 * Both collide through 0x44B0 - the **player-only** collision entry - so
 * shots pass straight through them; the generic sweep must skip these types.
 * Collection rides the normal collision remap and then *undoes* it: the
 * handler notices its own active bit was cleared, restores the player to
 * 0x81, grants an invincibility window, applies the effect and clears itself.
 */
const TYPE_POWER_CHIP = 63;
const TYPE_FIRE_UPGRADE = 83;
export const PICKUP_TYPES = new Set([TYPE_POWER_CHIP, TYPE_FIRE_UPGRADE]);

/** Colour per fire number for the shadow's digit form (0x8EAF). */
const SHADOW_COLOR_TABLE = 0x8eaf;
const CHIP_PICKUP_SFX = 0x17;

function playerTouches(pool, rom, slot) {
  const b = slot * ENTITY_STRIDE;
  if (pool.slots[0x01] === 0) return false;
  if (pool.type(0) !== 0x01) return false; // dead/dying player collects nothing
  const bounds = hitbox(pool.slots, b, rom);
  return hitboxOverlaps(pool.slots, 0, rom, bounds);
}

/** Shared collection epilogue: revive + shield the player (0x78C4 / 0x8E89). */
function reviveAndShield(pool, timer) {
  const s = pool.slots;
  s[0] = 0x81;
  s[0x05] |= 0x80;
  s[0x1b] = timer; // 0x40 for the chip; 0 (= ~256 frames) for the shadow
}

/** `handler_type63_power_chip` (0x78AF). */
function runPowerChip(pool, slot, ctx) {
  const s = pool.slots;
  const b = slot * ENTITY_STRIDE;
  if ((s[b] & 0x80) === 0) {
    s[b] |= 0x80; // spawned by a box; drift fields come from the spawner
    s[b + 0x0c] |= 0x01;
  }
  if (!ctx || !playerTouches(pool, ctx.rom, slot)) return true;

  const player = ctx.player;
  ctx.sound.playEvent(CHIP_PICKUP_SFX);
  reviveAndShield(pool, 0x40);
  const level = player.shotLevel + 1;
  if (level < 6) {
    // cap is 5: the increment is refused once level+1 reaches 6 (0x78DB)
    player.shotLevel = level;
    loadShotParams(player, ctx.rom);
  } else {
    // maxed: bonus counter, and every 5th maxed chip refreshes the fire
    ctx.state.bonusCounter = (ctx.state.bonusCounter + 1) & 0xff;
    player.maxedChips = (player.maxedChips + 1) & 0xff;
    if (player.maxedChips >= 5) {
      player.maxedChips = 0;
      fireSelect(player, ctx.rom, player.fireNum, ctx);
    }
  }
  pool.clear(slot);
  return false;
}

/** `handler_type83_black_shadow` (0x8E3A): the drifting fire upgrade. */
function runBlackShadow(pool, slot, ctx) {
  const s = pool.slots;
  const b = slot * ENTITY_STRIDE;
  const rom = ctx ? ctx.rom : null;
  if (!rom) return false;

  if ((s[b] & 0x80) === 0) {
    s[b] |= 0x80;
    s[b + 0x0c] = 0x01; // Y motion only
    s[b + 0x09] = 0xff; // vy = -0.125: a slow upward drift
    s[b + 0x08] = 0xe0;
    s[b + 0x1d] = rom.byte(SHADOW_COLOR_TABLE + s[b + 0x1c]); // per-fire colour
  }

  // 0x8E5D flicker: one frame in four the dark shadow form, else the digit.
  const phase = s[b + 0x1b];
  s[b + 0x1b] = (phase + 1) & 0xff;
  if ((phase & 0x03) === 0) {
    s[b + 0x03] = 0x24;
    s[b + 0x04] = 0x81;
  } else {
    s[b + 0x03] = 0x04;
    s[b + 0x04] = s[b + 0x1d];
  }

  if (ctx && playerTouches(pool, rom, slot)) {
    // 0x8E89: revive the player (timer 0 = the long shield), grab the weapon.
    reviveAndShield(pool, 0x00);
    ctx.state.bonusCounter = Math.max(0, ctx.state.bonusCounter - 5); // 0x8E95
    pool.clear(slot);
    fireSelect(ctx.player, rom, s[b + 0x1c] & 0x07, ctx); // fire_select(+0x1C)
    return false;
  }
  return true;
}

/**
 * Proto-box (type 68, 0x77A1) and the box enemy (types 4-6, 0x7826).
 *
 * The every-16th-kill bonus entity IS the box spawner: 0x77A1 converts itself
 * into a wave of **three** disguised boxes. Which box types appear is chosen
 * by a **score digit** (0xE104's low nibble indexes a 3-byte row at 0x77EA),
 * and how long they stay disguised by another (0xE105's high nibble into
 * 0x7808) - the classic score-driven item mechanic. X is random in
 * [0x38,0x77], the wave stepping +0x20 per box.
 *
 * Port deviation, noted: the ROM writes the second and third box straight
 * into IX+0x20/IX+0x40; this port allocates each through alloc_entity_slot so
 * live neighbours are not trampled.
 */
const PROTO_BOX_TYPE_TABLE = 0x77ea;
const PROTO_BOX_SAT_TABLE = 0x7808;

function runProtoBox(pool, slot, ctx) {
  const s = pool.slots;
  const rom = ctx.rom;
  const state = ctx.state;
  let x = ((prng() >> 8) & 0x3f) + 0x38;
  const typeRow = PROTO_BOX_TYPE_TABLE + (state.score[1] & 0x0f) * 3;
  const satRow = PROTO_BOX_SAT_TABLE + ((state.score[2] >> 4) & 0x0f) * 3;

  for (let i = 0; i < 3; i++) {
    const target = i === 0 ? slot : pool.allocEntitySlot();
    if (target < 0) break;
    const b = target * ENTITY_STRIDE;
    pool.clear(target);
    s[b] = rom.byte(typeRow + i); // 4/5/6, disguised (bit 7 clear)
    s[b + 0x02] = x;
    s[b + 0x03] = rom.byte(satRow + i); // sat_name doubles as the countdown
    s[b + 0x01] = 0x10; // enters at the top
    x = (x + 0x20) & 0xff;
  }
  return false; // slot 0 of the wave was rewritten; rerun next frame as a box
}

/** Box drop table, from the death branch at 0x7878 (selected by own type). */
const BOX_HP = 5;

function runBox(pool, slot, ctx) {
  const s = pool.slots;
  const b = slot * ENTITY_STRIDE;
  const rom = ctx.rom;

  if ((s[b] & 0x80) === 0) {
    // 0x782C: disguised - sat_name counts down; nothing shows (colour 0).
    s[b + 0x03] = (s[b + 0x03] - 1) & 0xff;
    if (s[b + 0x03] !== 0) return false;
    // 0x7830 reveal
    const child = pool.allocEntitySlot();
    if (child >= 0) {
      pool.clear(child);
      const cb = child * ENTITY_STRIDE;
      s[cb] = TYPE_COL_MARKER;
      s[cb + 0x03] = 0xd8; // box complement
      s[cb + 0x04] = 0x81;
      s[cb + 0x18] = 2;
      s[b + 0x1b] = child;
    }
    s[b + 0x19] = BOX_HP;
    s[b + 0x03] = 0xd4;
    s[b + 0x04] = 0x8f;
    s[b + 0x08] = 0xc0; // slow descent
    s[b + 0x09] = 0x00;
    s[b + 0x0c] = 0x01;
    s[b] |= 0x80;
  }

  // Multi-hit: the box soaks shots through its 5 HP (0x7904 undo-remap idiom).
  const hit = checkEntityCollisions(pool, rom, slot, ctx.player.fireMode);
  if (hit) {
    if (hit.hitBy === 0) {
      collisionResponse(pool, rom, slot, 0); // rams the player: both die
      return false;
    }
    pool.clear(hit.hitBy); // the shot is spent
    s[b + 0x19]--;
    s[b + 0x04] = 0x88 + s[b + 0x19]; // tint by remaining health (approx.)
    if (s[b + 0x19] === 0) {
      const boxType = s[b] & 0x7f;
      ctx.sound.playEvent(0x11);
      if (boxType === 6) {
        // 0x788A: become the power chip in place (type 0xBF, pattern 0x04)
        s[b] = 0x3f;
        s[b + 0x03] = 0x04;
        s[b + 0x04] = 0x8f;
        s[b + 0x0c] = 0x01;
        return false;
      }
      if (boxType === 4) {
        // 0x788F: three directed bullets - self dir 3, the complement
        // child's slot is reused for dir 5, a fresh slot gets dir 4.
        s[b] = 38;
        s[b + 0x1a] = 0x03;
        const child = s[b + 0x1b];
        if (pool.type(child) === TYPE_COL_MARKER) {
          const cb = child * ENTITY_STRIDE;
          s[cb] = 38;
          s[cb + 0x01] = s[b + 0x01];
          s[cb + 0x02] = s[b + 0x02];
          s[cb + 0x1a] = 0x05;
        }
        const third = pool.allocEntitySlot();
        if (third >= 0) {
          pool.clear(third);
          const tb = third * ENTITY_STRIDE;
          s[tb] = 38;
          s[tb + 0x01] = s[b + 0x01];
          s[tb + 0x02] = s[b + 0x02];
          s[tb + 0x1a] = 0x04;
        }
        return false;
      }
      // type 5: hand over to the type-35 explosion (score via +0x18)
      s[b + 0x18] = boxType;
      s[b] = 35;
      return false;
    }
  }
  return true;
}

/**
 * Enemy bullets (37 aimed, 38 directed) and the large descender (61).
 *
 * Type 37 (0x84DD): sprite 0x1C, speed 3, **aims at the player** (0x4C8B).
 * Type 38 (0x8501): same look, direction from its own +0x1A low nibble -
 * whoever spawns it chooses the spread.
 * Type 61 (0x8302): the every-16th-spawn large descender - enters at the top
 * on the side away from the player (X = 0x40 if the player is right of
 * centre, else 0xB0), falls at vy=+2, with an 0xFC complement child.
 */
function runLeadBullet(pool, slot, ctx, aimed) {
  const s = pool.slots;
  const b = slot * ENTITY_STRIDE;
  if ((s[b] & 0x80) === 0) {
    s[b + 0x17] = 0x03;
    s[b + 0x0c] = 0x03;
    s[b + 0x03] = 0x1c;
    s[b + 0x04] = 0x8f;
    if (ctx) {
      // 0x84F3 `player_pos_snapshot` both aims and applies the velocity.
      if (aimed) aimAtPlayer(pool, ctx.rom, b);
      else setVelocityFromDir(s, b, ctx.rom, s[b + 0x1a] & 0x0f, s[b + 0x17]);
    }
    s[b] |= 0x80;
    return true; // 0x84F6: init frame returns before entity_update
  }
  return true;
}

function runLargeDescender(pool, slot, ctx) {
  const s = pool.slots;
  const b = slot * ENTITY_STRIDE;
  if ((s[b] & 0x80) === 0) {
    const child = pool.allocEntitySlot();
    if (child < 0) {
      pool.clear(slot);
      return false;
    }
    pool.clear(child);
    const cb = child * ENTITY_STRIDE;
    s[cb] = TYPE_COL_MARKER;
    s[cb + 0x03] = 0xfc;
    s[cb + 0x04] = 0x81;
    s[cb + 0x18] = 2;
    s[b + 0x1b] = child;
    s[b + 0x02] = pool.slots[0x02] >= 0x78 ? 0x40 : 0xb0; // away from the player
    s[b + 0x01] = 0x10;
    s[b + 0x09] = 0x02; // vy = +2
    s[b + 0x0c] = 0x01;
    s[b + 0x03] = 0xf8;
    // 0x8327: the colour rotates - a global counter (0xE149) indexes the
    // 0x8EAF palette per spawn, and black (0x81) is swapped for white (0x8F).
    if (ctx) {
      const idx = ctx.state.descenderColorIdx & 0x07;
      ctx.state.descenderColorIdx = (ctx.state.descenderColorIdx + 1) & 0xff;
      s[b + 0x1d] = idx;
      let colour = ctx.rom.byte(0x8eaf + idx);
      if (colour === 0x81) colour = 0x8f;
      s[b + 0x04] = colour;
    } else {
      s[b + 0x04] = 0x8f;
    }
    s[b + 0x1e] = 0x20; // the mid-screen pause length
    s[b] |= 0x80;
    return true;
  }

  // 0x836B: the kill lottery. The walker soaks the hit itself so its death
  // can branch: shots-fired counter matching the score's low BCD digits turns
  // it into the invisible riser (type 62); a banked bonus counter >= 5 turns
  // it into a fire-upgrade shadow whose weapon is its own colour index
  // (+0x1D); otherwise the standard explosion.
  if (ctx) {
    const lottery = () => {
      // 0x8371: dec_encounter_a runs on every walker death, win or lose.
      if (ctx.spawn) {
        if (ctx.spawn.accHi > 0) ctx.spawn.accHi--;
        ctx.spawn.ctrl |= 0x01;
      }
      if ((ctx.player.shotsFired & 0x3f) === (ctx.state.score[0] & 0x3f)) {
        addScore(ctx.state, ctx.rom, ctx.rom.byte(0x4b29 + 61), ctx);
        s[b] = 0x3e; // type 62: rises away invisibly (0x8709)
        s[b + 0x0c] = 0x01;
        s[b + 0x09] = 0xff;
        s[b + 0x04] = 0x00;
        return;
      }
      if (ctx.state.bonusCounter >= 5) {
        addScore(ctx.state, ctx.rom, ctx.rom.byte(0x4b29 + 61), ctx);
        s[b] = 83; // shadow; its weapon = the walker's colour index
        s[b + 0x1c] = s[b + 0x1d];
        s[b + 0x05] = 0;
        s[b + 0x0c] = 0;
        return;
      }
      s[b + 0x18] = 61;
      s[b] = 35;
    };
    const hit = checkEntityCollisions(pool, ctx.rom, slot, ctx.player.fireMode);
    if (hit && hit.hitBy !== 0) {
      pool.clear(hit.hitBy);
      lottery();
      return false;
    } else if (hit) {
      collisionResponse(pool, ctx.rom, slot, 0); // rams the player
      // 0x836B checks the type AFTER the collision call, so a ram that
      // remapped the walker to 0x23 rolls the same lottery.
      if ((s[b] & 0x7f) === 35) lottery();
      return false;
    }
  }

  // 0x834A: descend to Y = 0x60, freeze there for 0x20 frames, then retreat
  // upward at 4px/frame - the walker's advance/pause/withdraw cycle.
  if (s[b + 0x01] === 0x60) {
    s[b + 0x0c] = 0x00;
    s[b + 0x1e] = (s[b + 0x1e] - 1) & 0xff;
    if (s[b + 0x1e] === 0) {
      s[b + 0x0c] = 0x01;
      s[b + 0x09] = 0xfc; // vy = -4
    }
  }
  return true;
}

/**
 * The luster trio (16/17/18). Three jump-table entries (0x7BEB / 0x7C8A /
 * 0x7CB3) with per-type inits that all fall into one shared tail at 0x7BFF:
 * pick a side - (X=0x40, E=1) or (X=0xB0, E=7), random bit - spawn the 0x7C
 * complement child, sat 0x74, then a `SUB 0x92` type switch applies the
 * finishing fields (16: +0x1D=E; 17: target_x=D, i.e. it weaves around its
 * own spawn column; 18: fixed X=0x60, target_x=0xFF - a rightward sweep).
 */
function runLuster(pool, slot, ctx) {
  const s = pool.slots;
  const b = slot * ENTITY_STRIDE;
  const type = s[b] & 0x7f;
  if ((s[b] & 0x80) !== 0) return runLusterActive(pool, s, b, type, ctx);

  const child = pool.allocEntitySlot();
  if (child < 0) {
    pool.clear(slot);
    return false;
  }
  pool.clear(child);
  const cb = child * ENTITY_STRIDE;
  s[cb] = TYPE_COL_MARKER;
  s[cb + 0x03] = 0x7c;
  s[cb + 0x04] = 0x81;
  s[cb + 0x18] = 2;
  s[b + 0x1b] = child;

  const right = (prng() & 1) !== 0;
  const d = right ? 0xb0 : 0x40;
  const e = right ? 0x07 : 0x01;

  s[b + 0x01] = 0x10;
  s[b + 0x03] = 0x74;
  s[b + 0x09] = 0x02; // vy = +2, all three fall

  switch (type) {
    case 16: // 0x7BEB: plain faller from a random side
      s[b + 0x0c] = 0x01;
      s[b + 0x1e] = 0xc0;
      s[b + 0x02] = d;
      s[b + 0x04] = 0x8e;
      s[b + 0x1d] = e;
      break;
    case 17: // 0x7C8A: weaves around its spawn column (X-homing to X=D)
      s[b + 0x17] = 0x04;
      s[b + 0x0c] = 0x13;
      s[b + 0x0b] = 0xfc; // vx = -4
      s[b + 0x16] = 0x40; // x_accel
      s[b + 0x1e] = 0xe0;
      s[b + 0x02] = d;
      s[b + 0x04] = 0x8e;
      s[b + 0x14] = d; // target_x = own column
      break;
    default: // 18, 0x7CB3: from X=0x60 sweeping right toward 0xFF
      s[b + 0x17] = 0x02;
      s[b + 0x0c] = 0x13;
      s[b + 0x16] = 0x0e;
      s[b + 0x1d] = 0x30;
      s[b + 0x02] = 0x60;
      s[b + 0x04] = 0x8b;
      s[b + 0x0b] = 0xff; // vx = -1
      s[b + 0x14] = 0xff; // target_x
      break;
  }
  s[b] |= 0x80;
  return true;
}

/**
 * The luster's active frame — **this is where lusters shoot**, and it was
 * missing entirely: the port used to return straight out of the init check,
 * so a luster fell past harmlessly.
 *
 * Types 16/17 (0x7C43) fire on a **Y grid**. +0x1E is a mask, and the two
 * tests `((Y + 0x18) & mask) - 0x18 == Y` and `((Y + 0x10) & mask) - 0x10 == Y`
 * pick out two phases of the fall: the first just swaps to the closed sprite
 * pair (0x74 / 0x7C), the second opens it (0x78 / 0x80) **and launches a
 * type-38 fragment in the direction held in +0x1D**. Every other row it just
 * falls.
 *
 * Type 18 (0x7CD8) uses a plain countdown in +0x1D instead: at 0 it reloads
 * 0x30, shows the closed sprite and fires a **type-37 aimed bullet**; at 8 it
 * opens the sprite again.
 */
function runLusterActive(pool, s, b, type, ctx) {
  const child = s[b + 0x1b] * ENTITY_STRIDE;

  if (type === 18) {
    s[b + 0x1d] = (s[b + 0x1d] - 1) & 0xff;
    if (s[b + 0x1d] === 0) {
      s[b + 0x1d] = 0x30;
      s[b + 0x03] = 0x74;
      s[child + 0x03] = 0x7c;
      const q = pool.allocEntitySlot();
      if (q >= 0) {
        const qb = q * ENTITY_STRIDE;
        s[qb] = 0x25; // type 37: aims itself at the player
        s[qb + 0x1a] = 0;
        s[qb + 0x01] = s[b + 0x01];
        s[qb + 0x02] = s[b + 0x02];
      }
    }
    if (s[b + 0x1d] === 0x08) {
      s[b + 0x03] = 0x78;
      s[child + 0x03] = 0x80;
    }
    return true;
  }

  const mask = s[b + 0x1e];
  const y = s[b + 0x01];
  if (((((y + 0x18) & 0xff) & mask) - 0x18 + 0x100) % 0x100 === y) {
    s[b + 0x03] = 0x74; // 0x7C7F: closed
    s[child + 0x03] = 0x7c;
    return true;
  }
  if (((((y + 0x10) & 0xff) & mask) - 0x10 + 0x100) % 0x100 !== y) return true;
  s[b + 0x03] = 0x78; // 0x7C66: open, and fire
  s[child + 0x03] = 0x80;
  const q = pool.allocEntitySlot();
  if (q < 0) return true;
  const qb = q * ENTITY_STRIDE;
  s[qb] = 0x26; // type 38: directed fragment
  s[qb + 0x1a] = s[b + 0x1d];
  s[qb + 0x01] = s[b + 0x01];
  s[qb + 0x02] = s[b + 0x02];
  void ctx;
  return true;
}

/**
 * Umber (types 7/8, handler 0x791D). Descends from the top at centre X=0x78
 * with vy=+3 and a Y-homing pull toward **target 0** (accel 0x10) - i.e. a
 * built-in deceleration. The exact frame the velocity word crosses 0x0000 it
 * opens (sat 0xE0) and releases its payload; the homing then drives vy
 * negative, the umbrella folds (0xDC) and it floats back up off-screen. The
 * single-frame zero crossing is what makes the burst fire exactly once.
 *
 * Type 7 payload: seven type-38 bullets, directions 4,5,2,7,3,6,1 (0x79B7) -
 * a downward fan. Type 8 (colour 0x8B): the 0x79CC pair - two type-0x29 (41)
 * entities, the first with +0x1A = 5. Type 41's own handler (0x8556) is not
 * ported, so the pair flies as directed type-38 fragments on dirs 5/3.
 */
const UMBER_BURST_DIRS = 0x79b7;

function runUmber(pool, slot, ctx) {
  const s = pool.slots;
  const b = slot * ENTITY_STRIDE;
  const type = s[b] & 0x7f;

  if ((s[b] & 0x80) === 0) {
    const child = pool.allocEntitySlot();
    if (child < 0) {
      pool.clear(slot);
      return false;
    }
    pool.clear(child);
    const cb = child * ENTITY_STRIDE;
    s[cb] = TYPE_COL_MARKER;
    s[cb + 0x03] = 0xe4;
    s[cb + 0x04] = 0x81;
    s[cb + 0x18] = 2;
    s[b + 0x1b] = child;

    s[b + 0x01] = 0x10;
    s[b + 0x02] = 0x78;
    s[b + 0x17] = 0x01; // one homing iteration per frame
    s[b + 0x09] = 0x03; // vy = +3
    s[b + 0x15] = 0x10; // y-accel toward target_y = 0: deceleration
    s[b + 0x0c] = 0x09; // Y motion + Y homing
    s[b + 0x03] = 0xdc;
    s[b + 0x04] = type === 8 ? 0x8b : 0x8f; // 0x79C7 colour patch for type 8
    if (type === 9) {
      // 0x7A04: the missile umber - light green, its own sprite pair, and an
      // eight-frame fire timer.
      s[b + 0x03] = 0xe0;
      s[b + 0x04] = 0x83;
      s[cb + 0x03] = 0xe8;
      s[b + 0x1d] = UMBER9_FIRE_PERIOD;
    }
    s[b] |= 0x80;
    return true;
  }

  if (type === 9) {
    // 0x7A12: every eight frames, one type-20 homing bullet from wherever it
    // happens to be in the weave - the steady missile stream.
    s[b + 0x1d] = (s[b + 0x1d] - 1) & 0xff;
    if (s[b + 0x1d] === 0) {
      s[b + 0x1d] = UMBER9_FIRE_PERIOD;
      const q = pool.allocEntitySlot();
      if (q >= 0) {
        const e = q * ENTITY_STRIDE;
        s[e] = 0x14;
        s[e + 0x01] = s[b + 0x01];
        s[e + 0x02] = s[b + 0x02];
      }
    }
    return true; // type 9 skips the sprite weave of 7/8 (0x7A12 -> 0x79AE)
  }

  const vy = s[b + 0x09];
  const child = s[b + 0x1b];
  const cb = child * ENTITY_STRIDE;
  if (vy === 0xff) {
    s[b + 0x03] = 0xdc; // folding, on the way back up
    if (pool.type(child) === TYPE_COL_MARKER) s[cb + 0x03] = 0xe4;
  } else if (vy === 0x00) {
    s[b + 0x03] = 0xe0; // open
    if (pool.type(child) === TYPE_COL_MARKER) s[cb + 0x03] = 0xe8;
    if (s[b + 0x08] === 0x00) {
      // exact zero crossing: release the payload once (0x798C)
      const count = type === 8 ? 2 : 7;
      for (let i = 0; i < count; i++) {
        const q = pool.allocEntitySlot();
        if (q < 0) break;
        pool.clear(q);
        const e = q * ENTITY_STRIDE;
        s[e] = 38;
        s[e + 0x01] = s[b + 0x01];
        s[e + 0x02] = s[b + 0x02];
        s[e + 0x1a] =
          type === 8 ? (i === 0 ? 5 : 3) : ctx.rom.byte(UMBER_BURST_DIRS + i);
      }
    }
  }
  return true;
}

/**
 * The type-72 ORB (handler 0x8983, kb: handler_type72_base_core) - what a
 * totem releases when destroyed. Rises slowly with a two-phase animation and
 * runs a yellow->black life counter; its effect fires on PLAYER TOUCH only
 * (0x44B0 - shots pass through):
 *   yellow (+0x1E != 0): explode_enemies + SFX 0x13
 *   black  (+0x1E == 0): WARP - the round jumps to the stream pointer the
 *                        idol table left in +0x1C/1D
 */
const ORB_ANIM_1 = 0x8a16;
const ORB_ANIM_2 = 0x8a1e;

function runOrb(pool, slot, ctx) {
  const s = pool.slots;
  const b = slot * ENTITY_STRIDE;
  if (!ctx) return false;

  if ((s[b] & 0x80) === 0) {
    s[b] |= 0x80;
    s[b + 0x09] = 0xff; // rise, ~0.03 px/f
    s[b + 0x08] = 0xf8;
    s[b + 0x0c] = 0x05; // Y motion + animate
    s[b + 0x11] = ORB_ANIM_1 & 0xff;
    s[b + 0x12] = ORB_ANIM_1 >> 8;
    s[b + 0x0f] = 0x00;
    s[b + 0x10] = 0x04;
    s[b + 0x0d] = 0x01;
    s[b + 0x0e] = 0x04;
    s[b + 0x1e] = 0x04; // yellow phase units (0x89B1)
  }

  // 0x89BB exact: while yellow, +0x1B free-runs down (8-bit, so ~256 frames
  // per unit); each wrap burns one +0x1E. When the last one goes: an orb from
  // a plain totem (subtype 0x46, type 70) simply vanishes - ONLY type 71's
  // orbs (subtype 0x47+) turn black and become the warp.
  if (s[b + 0x1e] !== 0) {
    s[b + 0x1b] = (s[b + 0x1b] - 1) & 0xff;
    if (s[b + 0x1b] === 0) {
      s[b + 0x1e]--;
      if (s[b + 0x1e] === 0) {
        if (s[b + 0x1f] === 0x46) {
          pool.clear(slot);
          return false;
        }
        s[b + 0x11] = ORB_ANIM_2 & 0xff; // black: second anim, faster rise
        s[b + 0x12] = ORB_ANIM_2 >> 8;
        s[b + 0x08] = 0xf0;
      }
    }
  }

  if (playerTouches(pool, ctx.rom, slot)) {
    if (s[b + 0x1e] !== 0) {
      // yellow: clear the sky
      fireExplodeEnemies(ctx);
      ctx.sound.playEvent(0x13);
    } else {
      // 0x8A05: black orb - the destination goes into 0xE722 and the
      // level-complete flag is raised; `level_complete_handler` does the rest
      // on the next main-loop pass. It is NOT an in-place script jump.
      const target = s[b + 0x1c] | (s[b + 0x1d] << 8);
      if (target) {
        ctx.scroll.warpTarget = target;
        ctx.state.flowFlags |= 0x20; // 0x8A0E: SET 5,(0xE102)
      }
    }
    pool.clear(slot);
    return false;
  }
  return true;
}

/**
 * The crater stamper (0x88ED): debris tiles written into the scroll ring AND
 * the name table, so the wreckage scrolls with the terrain. Strip format:
 * [rowCount] then per row [width][tiles...]. The strips overlap in ROM to
 * save bytes (84's tail is 85's head).
 */
function stampCrater(ctx, strip, xPx, yPx) {
  const rom = ctx.rom;
  const scroll = ctx.scroll;
  let a = strip;
  const rows = rom.byte(a++);
  const col = xPx >> 3;
  const row = yPx >> 3;
  for (let r = 0; r < rows; r++) {
    const w = rom.byte(a++);
    for (let i = 0; i < w; i++) {
      const tile = rom.byte(a++);
      const rr = row + r;
      const cc = col + i;
      if (rr >= 0 && rr < 24 && cc >= 0 && cc < 24) {
        scroll.ring[((scroll.ringRow + rr) % 24) * 24 + cc] = tile;
        ctx.screen.nameTable[rr * 32 + cc] = tile;
      }
    }
  }
}

/**
 * Base projectiles, types 42 / 43 / 45 (0x85CC, 0x85D6, 0x85EE).
 *
 * All three share the burst-fragment body: sprite 0x1C in white, behaviour
 * flags 3 (both axes), a 3-frame collision box. What differs is the aim.
 *
 * - **42** (0x85CC) takes a snapshot of where the player is (0x84F3) and then
 *   scrambles its own velocity bytes with the refresh register (0x85DD), so it
 *   drifts rather than tracks - the classic base "spray".
 * - **43** (0x85D6) is the directed one: 0x851D turns its +0x1A parameter into
 *   a velocity, which is why the segments' firing geometry is all expressed as
 *   direction codes.
 * - **45** (0x85EE) is the light bar: it re-aims every 0x28 frames by nudging
 *   +0x1A by a random +/-4, and flips between two sprites as it travels.
 */
function runBaseProjectile(pool, slot, ctx, type) {
  const s = pool.slots;
  const b = slot * ENTITY_STRIDE;
  const first = (s[b] & 0x80) === 0;

  if (type === 45) {
    if (first) {
      // 0x85F4: a 2-3 frame hitbox, then the shared init at 0x850B.
      s[b + 0x17] = 2 + ((prng() >> 3) & 1);
      s[b + 0x0c] = 0x03;
      s[b + 0x03] = 0x1c;
      s[b + 0x04] = 0x8f;
      s[b + 0x19] = 0x03;
      s[b + 0x1c] = 0x28;
      s[b] |= 0x80;
    }
    s[b + 0x1c] = (s[b + 0x1c] - 1) & 0xff;
    if (s[b + 0x1c] === 0) {
      s[b + 0x1c] = 0x28; // 0x8604 reload
      if ((prng() >> 3) & 1) {
        // 0x8613: turn by a random +4 / -4 and re-derive the velocity.
        const turn = (prng() & 0x08) + s[b + 0x1a] - 0x04;
        s[b + 0x1a] = turn & 0xff;
        setVelocityFromDir(s, b, ctx.rom, turn & 0x0f, s[b + 0x17]);
      }
    } else {
      // 0x8625: the bar alternates between sprites 0x18 and 0x20.
      s[b + 0x03] = 0x18 + ((s[b + 0x1c] & 1) << 3);
    }
    return true;
  }

  if (first) {
    s[b + 0x17] = 0x03;
    s[b + 0x03] = 0x1c;
    s[b + 0x04] = 0x8f;
    s[b + 0x0c] = 0x03;
    if (type === 43) {
      setVelocityFromDir(s, b, ctx.rom, s[b + 0x1a] & 0x0f, s[b + 0x17]); // 0x851D
      s[b] = 0xa6;
    } else {
      // 0x84F3: the shared init at 0x84E3 calls `player_pos_snapshot`, which
      // aims at the player AND writes the velocity. The scramble below then
      // jitters it, so a type-42 is an aimed shot with a wobble - not a
      // random drift.
      aimAtPlayer(pool, ctx.rom, b);
      s[b] = 0xa5;
    }
  }
  if (type === 42) {
    // 0x85DD: the two *fraction* bytes are XOR-stirred by the refresh
    // register, so the aim holds but the shot wobbles around it.
    s[b + 0x0a] ^= prng() & 0xff;
    s[b + 0x08] ^= prng() & 0xff;
  }
  return true;
}

/**
 * `spawn_col_marker` (0x71DA): allocate the black "complement" half of a
 * two-sprite enemy. The child is a type-39 keepalive whose only job is to
 * carry a second sprite pattern; `postTypeHandler` pushes it right after the
 * parent each frame.
 *
 * On failure the ROM discards the caller's return address and clears the
 * parent outright, which is why every caller here bails on -1.
 *
 * @returns {number} the child slot, or -1
 */
function spawnColMarker(pool, s, b) {
  const child = pool.allocEntitySlot();
  if (child < 0) return -1;
  pool.clear(child);
  const cb = child * ENTITY_STRIDE;
  s[cb] = TYPE_COL_MARKER;
  s[cb + 0x04] = 0x81; // black
  s[cb + 0x18] = 2;
  s[b + 0x1b] = child;
  return child;
}

/**
 * The **veybar** family, types 22-25 (0x7D0F for 22/23, 0x7DB4 for 24/25,
 * merging at 0x7D2D and sharing the active body at 0x7D4C).
 *
 * A two-sprite enemy that enters from one side, decelerates as it descends,
 * and part-way down **morphs** through four sprite frames. At exactly one of
 * those frames it fires - and types 22/23 additionally re-aim themselves at
 * the player and switch on horizontal motion, so they dive.
 *
 * The left/right coin flip is the Z80 refresh register, not the PRNG.
 */
function runVeybar(pool, slot, ctx, type) {
  const s = pool.slots;
  const b = slot * ENTITY_STRIDE;

  if ((s[b] & 0x80) === 0) {
    let x;
    let vxInt;
    if (type <= 23) {
      // 0x7D15: X = 200 moving left, or X = 40 moving right.
      if (prng() & 1) {
        x = 0x28;
        vxInt = 0x01;
      } else {
        x = 0xc8;
        vxInt = 0xff;
      }
      s[b + 0x0c] = 0x09; // Y motion + Y homing
      s[b + 0x04] = 0x83; // light green
      s[b + 0x1d] = 0x50; // morph countdown
    } else {
      // 0x7DBB: the fast pair also homes horizontally, toward 0xFF or 0x00.
      if (prng() & 1) {
        s[b + 0x14] = 0x00;
        x = 0x38;
        vxInt = 0x03;
      } else {
        s[b + 0x14] = 0xff;
        x = 0xb8;
        vxInt = 0xfd;
      }
      s[b + 0x0c] = 0x1b; // Y+X motion, Y+X homing
      s[b + 0x16] = 0x10; // X-homing step
      s[b + 0x04] = 0x89; // light red
      s[b + 0x1d] = 0x58;
    }
    // 0x7D2D shared tail.
    const child = spawnColMarker(pool, s, b);
    if (child < 0) {
      pool.clear(slot);
      return false;
    }
    s[child * ENTITY_STRIDE + 0x03] = 0x98;
    s[b + 0x0b] = vxInt;
    s[b + 0x02] = x;
    s[b + 0x17] = 0x01; // one homing iteration per frame
    s[b + 0x09] = 0x04; // vy = +4.0
    s[b + 0x15] = 0x14; // Y-homing step; target +0x13 is never written, so 0
    s[b + 0x03] = 0x84;
    s[b] |= 0x80;
    // falls through into the active body on the same frame
  }

  const child = s[b + 0x1b];
  if ((s[b + 0x05] & 0x01) === 0) {
    s[b + 0x1d] = (s[b + 0x1d] - 1) & 0xff;
    if (s[b + 0x1d] === 0) s[b + 0x05] |= 0x01; // 0x7D60: latch, morph over
    const c = s[b + 0x1d];
    // 0x7D6B: the RRCA/AND/CP dance is simply "every 16th count below 0x40".
    if (c < 0x40 && (c & 0x0f) === 0) {
      const e = c >> 2;
      s[b + 0x03] = (0x94 - e) & 0xff;
      const markerName = (0x94 - e + 0x14) & 0xff;
      s[child * ENTITY_STRIDE + 0x03] = markerName;
      if (markerName === 0xa0) veybarFire(pool, s, b, ctx, type); // c == 0x20
    }
  }
  return true;
}

/**
 * 0x7D8C. `SRL A` throws bit 0 away, so the `CP 0x4B` gate matches the whole
 * **pair** 22/23 - not type 22 alone. Types 24/25 fail it but still fall into
 * the shared spawn at 0x7DAB, so every veybar fires a lead bullet.
 */
function veybarFire(pool, s, b, ctx, type) {
  if (type <= 23) {
    s[b + 0x17] = 0x04; // speed multiplier the aim is scaled by
    aimAtPlayer(pool, ctx.rom, b); // 0x7D99 aim + 0x7D9C apply
    s[b + 0x17] = 0x01;
    s[b + 0x15] = 0x0c; // gentler Y homing from here on
    s[b + 0x0c] |= 0x02; // 0x7DA7: switch X motion on - now it dives
  }
  const child = pool.allocEntitySlot();
  if (child < 0) return;
  const cb = child * ENTITY_STRIDE;
  s[cb] = 0x25; // type 37, the lead bullet
  s[cb + 0x01] = s[b + 0x01];
  s[cb + 0x02] = s[b + 0x02];
}

/** Per-type prologues for the swoopers (0x7DE2 / 0x7DF3 / 0x7E78 / 0x7E86). */
const SWOOPER_INIT = new Map([
  //          X     child   vx word  anim table  spawn countdown
  [26, { x: 0xc8, child: 0x25, vx: 0xff40, anim: 0x7e68, count: 0x18 }],
  [27, { x: 0x28, child: 0x14, vx: 0x00c0, anim: 0x7e68, count: 0x18 }],
  [28, { x: 0xc0, child: 0x3b, vx: 0xfe00, anim: 0x7e70, count: 0x04 }],
  [29, { x: 0x30, child: 0x29, vx: 0x0200, anim: 0x7e70, count: 0x04 }],
]);

/**
 * The **edge swoopers**, types 26-29. Four prologues that merge at 0x7E06 and
 * share the body at 0x7E3F: each enters from a fixed side, arcs down and back
 * out (Y homing on a target of 0, so `vy` decays and reverses), and drops a
 * child every 32 frames.
 *
 * Note they are *invisible for their first three frames*: +0x03 and +0x04 are
 * never initialised, so the sprite stays pattern 0 / colour 0 until the
 * animation timer first fires on frame 4. They are collidable throughout.
 */
function runEdgeSwooper(pool, slot, ctx, type) {
  const s = pool.slots;
  const b = slot * ENTITY_STRIDE;

  if ((s[b] & 0x80) === 0) {
    const init = SWOOPER_INIT.get(type);
    s[b + 0x1d] = init.child;
    s[b + 0x11] = init.anim & 0xff;
    s[b + 0x12] = init.anim >> 8;
    s[b + 0x02] = init.x;
    s[b + 0x0a] = init.vx & 0xff;
    s[b + 0x0b] = init.vx >> 8;
    s[b + 0x1e] = init.count;
    if (spawnColMarker(pool, s, b) < 0) {
      pool.clear(slot);
      return false;
    }
    s[b + 0x08] = 0x80;
    s[b + 0x09] = 0x02; // vy = +2.5
    s[b + 0x17] = 0x01;
    s[b + 0x15] = 0x07; // Y-homing step, target 0 -> it arcs back out
    s[b + 0x0c] = 0x0f; // Y+X motion, animate, Y homing
    s[b + 0x10] = 0x04; // 4 animation frames
    s[b + 0x0d] = 0x04;
    s[b + 0x0e] = 0x04;
    s[b] |= 0x80;
  }

  // 0x7E3F: the drop timer reloads to 32 whether or not a slot was free.
  s[b + 0x1e] = (s[b + 0x1e] - 1) & 0xff;
  if (s[b + 0x1e] === 0) {
    s[b + 0x1e] = 0x20;
    const child = pool.allocEntitySlot();
    if (child >= 0) {
      const cb = child * ENTITY_STRIDE;
      s[cb] = s[b + 0x1d];
      s[cb + 0x1a] = 0x04; // straight down
      s[cb + 0x01] = s[b + 0x01];
      s[cb + 0x02] = s[b + 0x02];
    }
  }
  return true;
}

/**
 * The **duster**, type 10 (0x7A2A) — the most common payload the wave
 * spawners send, and the first entry in `base_spawner_spawn_table`.
 *
 * It picks a random column, then homes horizontally toward whichever screen
 * edge it started nearest: 0x7A3D compares the drawn X against 0x88 and sets
 * the target (+0x14) to 0x00 for the left half or 0xFF for the right, so a
 * duster always drifts *outward* while it falls.
 */
function runDuster(pool, slot, ctx) {
  const s = pool.slots;
  const b = slot * ENTITY_STRIDE;
  if ((s[b] & 0x80) !== 0) return true;

  const child = spawnColMarker(pool, s, b);
  if (child < 0) {
    pool.clear(slot);
    return false;
  }
  s[child * ENTITY_STRIDE + 0x03] = 0x5c;
  randomXPos(s, b);
  // 0x7A39: target 0 on the right half, 0xFF (via DEC from 0) on the left.
  s[b + 0x14] = s[b + 0x02] >= 0x88 ? 0x00 : 0xff;
  s[b + 0x03] = 0x58;
  s[b + 0x04] = 0x89;
  s[b + 0x0c] = 0x13; // Y+X motion, X homing
  s[b + 0x08] = 0x00;
  s[b + 0x09] = 0x03; // vy = +3
  s[b + 0x16] = 0x08; // X-homing step
  s[b + 0x17] = 0x01;
  s[b] |= 0x80;
  return true;
}

/**
 * **Lead homing bullet**, type 20 (0x8668). Dropped by edge swooper 27. It
 * homes on X target 0xFF - i.e. it always curves right - while carrying a
 * random horizontal velocity seeded from the PRNG, so a volley fans out.
 */
function runLeadHoming(pool, slot, ctx) {
  const s = pool.slots;
  const b = slot * ENTITY_STRIDE;
  if ((s[b] & 0x80) !== 0) return true;
  s[b + 0x03] = 0x1c;
  s[b + 0x04] = 0x8f;
  s[b + 0x0c] = 0x0b; // Y+X motion, Y homing
  s[b + 0x13] = 0xff; // Y-homing target
  s[b + 0x15] = 0x0c;
  s[b + 0x17] = 0x01;
  const r = prng();
  s[b + 0x0b] = (((r >> 8) & 0x03) - 2) & 0xff; // vx integer in -2..+1
  s[b + 0x0a] = r & 0xff;
  s[b] |= 0x80;
  return true;
}

/**
 * **Light bar**, type 21 (0x8635) — the projectile most ground guns fire.
 * Its direction comes from +0x1A, set by whoever spawned it, and it announces
 * itself with SFX 0x16. While flying it re-rolls its own colour every frame
 * from the refresh register, which is what makes it strobe.
 */
function runLightBar(pool, slot, ctx) {
  const s = pool.slots;
  const b = slot * ENTITY_STRIDE;
  if ((s[b] & 0x80) === 0) {
    s[b + 0x17] = 0x04;
    s[b + 0x03] = 0x18;
    setVelocityFromDir(s, b, ctx.rom, s[b + 0x1a] & 0x0f, s[b + 0x17]);
    s[b + 0x0c] = 0x03; // Y+X motion
    s[b] |= 0x80;
    ctx.sound.playEvent(0x16);
    return false; // 0x8656: the init path returns through play_sound_event
  }
  s[b + 0x04] = (prng() & 0x0f) | 0x80; // 0x8659: strobe
  return true;
}

/**
 * The **descender/dart family**, types 56-59 (0x819D / 0x81D1 / 0x8247 /
 * 0x8269), all merging into the same setup tail at 0x81AC and the same active
 * body at 0x81C3.
 *
 * All four look identical in flight - sprite plus a colour that XORs by 0x09
 * every frame, so they strobe. What differs is how many complement children
 * they carry and what happens when their 0x20-frame fuse burns out:
 *
 * - **56** flies straight down and simply keeps going.
 * - **57** carries one child; **58** carries two.
 * - **57/58** (0x81E6) aim at the player when the fuse expires, play SFX
 *   0x15, and **turn themselves and their children into type-59 darts**
 *   spread one direction step apart - a three-way volley from a type 58.
 * - **59** is that dart: it takes its direction from +0x1A and never
 *   transforms.
 */
function runDescenderDart(pool, slot, ctx, type) {
  const s = pool.slots;
  const b = slot * ENTITY_STRIDE;
  const rom = ctx.rom;

  if ((s[b] & 0x80) === 0) {
    let dir = 0x04; // straight down for 56/57/58
    if (type === 56) {
      randomXPos(s, b);
      s[b + 0x03] = 0x70;
    } else if (type === 57) {
      if (spawnColMarker(pool, s, b) < 0) {
        pool.clear(slot);
        return false;
      }
      randomXPos(s, b);
      s[b + 0x03] = 0x6c;
    } else if (type === 58) {
      // 0x824D: two children. The first is stashed in +0x1D/+0x1E (the ROM
      // backs the returned pointer up by 3 to reach the slot base), the
      // second in the usual +0x1B.
      const first = spawnColMarker(pool, s, b);
      if (first < 0) {
        pool.clear(slot);
        return false;
      }
      s[b + 0x1d] = first;
      s[b + 0x1e] = 0;
      if (spawnColMarker(pool, s, b) < 0) {
        pool.clear(slot);
        return false;
      }
      randomXPos(s, b);
      s[b + 0x03] = 0x68;
    } else {
      dir = s[b + 0x1a] & 0x0f; // 0x8270: the dart keeps its spawner's aim
      s[b + 0x03] = 0x70;
    }
    // 0x81AC shared tail.
    s[b + 0x17] = 0x05;
    setVelocityFromDir(s, b, rom, dir, s[b + 0x17]);
    s[b + 0x0c] = 0x03;
    s[b + 0x04] = 0x8f;
    s[b + 0x1f] = 0x20; // the fuse
    s[b] |= 0x80;
  }

  if (type === 57 || type === 58) {
    // 0x81E6: keep the children alive, then run the fuse down.
    s[s[b + 0x1b] * ENTITY_STRIDE + 0x18] = 2;
    if (type === 58) s[s[b + 0x1d] * ENTITY_STRIDE + 0x18] = 2;
    s[b + 0x1f] = (s[b + 0x1f] - 1) & 0xff;
    if (s[b + 0x1f] === 0) {
      ctx.sound.playEvent(0x15);
      const e = aimDirection(pool, rom, b); // 0x820C: aim only
      s[b] = 0x3b; // become a dart, one step anticlockwise of the aim
      s[b + 0x1a] = (e - 1) & 0xff;
      const c1 = s[b + 0x1b] * ENTITY_STRIDE;
      s[c1] = 0x3b;
      s[c1 + 0x01] = s[b + 0x01];
      s[c1 + 0x02] = s[b + 0x02];
      s[c1 + 0x1a] = (e + 1) & 0xff;
      if (type === 58) {
        const c2 = s[b + 0x1d] * ENTITY_STRIDE;
        s[c2] = 0x3b;
        s[c2 + 0x01] = s[b + 0x01];
        s[c2 + 0x02] = s[b + 0x02];
        s[c2 + 0x1a] = e & 0xff; // 0x8244: the middle of the three
      }
      return false;
    }
  }

  s[b + 0x04] ^= 0x09; // 0x81C6: the strobe
  return true;
}

/**
 * **Type 41**, the curving shot (0x852F). Dropped by edge swooper 29.
 *
 * It keeps two velocities: a fixed forward one, saved into +0x1C..+0x1F at
 * init (0x8570 copies +0x08..+0x0B there), and a rotating perpendicular one
 * that starts four steps to the side and turns one step every other frame -
 * anticlockwise or clockwise depending on +0x1A bit 4. Each frame the two are
 * **summed**, which is what bends the trajectory into an arc.
 */
function runCurvingShot(pool, slot, ctx) {
  const s = pool.slots;
  const b = slot * ENTITY_STRIDE;
  const rom = ctx.rom;

  if ((s[b] & 0x80) === 0) {
    s[b + 0x03] = 0x1c;
    s[b + 0x04] = 0x8f;
    s[b + 0x17] = 0x02;
    s[b + 0x0c] = 0x03;
    const dir = s[b + 0x1a] & 0x0f;
    // 0x854B: bit 4 picks which side the perpendicular starts on.
    s[b + 0x1b] = (dir + (s[b + 0x1a] & 0x10 ? -4 : 4)) & 0x0f;
    setVelocityFromDir(s, b, rom, dir, s[b + 0x17]);
    for (let i = 0; i < 4; i++) s[b + 0x1c + i] = s[b + 0x08 + i]; // 0x8570
    s[b] |= 0x80;
    s[b + 0x15] = 0x02;
    s[b + 0x17] = 0x04;
    return false; // 0x857E: the init frame returns before entity_update
  }

  s[b + 0x15] = (s[b + 0x15] - 1) & 0xff;
  if (s[b + 0x15] === 0) {
    s[b + 0x15] = 0x02;
    s[b + 0x1b] = (s[b + 0x1b] + (s[b + 0x1a] & 0x10 ? -1 : 1)) & 0xff;
  }
  setVelocityFromDir(s, b, rom, s[b + 0x1b] & 0x0f, s[b + 0x17]);
  // 0x859F: add the saved forward velocity back on, 16 bits at a time.
  const addWord = (at, from) => {
    const sum = ((s[b + at + 1] << 8) | s[b + at]) + ((s[b + from + 1] << 8) | s[b + from]);
    s[b + at] = sum & 0xff;
    s[b + at + 1] = (sum >> 8) & 0xff;
  };
  addWord(0x08, 0x1c);
  addWord(0x0a, 0x1e);
  return true;
}

/**
 * `handler_type84_wide_variant`'s firing body (0x8EC7). Each of the three
 * types reloads the countdown to its own cadence and aims differently:
 *
 * - **84** (0x8F13) — every 10 frames, a type-38 fragment on a **rotating**
 *   direction, `(+0x1E * 2) & 0x0F`, so it sweeps the full circle.
 * - **85** (0x8EFC) — every 0x18 frames, a type-21 light bar sent to the side
 *   the player is on. It picks a *different* pair of directions when the
 *   scroll has stalled (0xE710 == 0, i.e. during a base fight): 0/8 standing
 *   still versus 1/7 while the terrain moves.
 * - **86** (0x8EE3) — every 8 frames, a type-21 on a four-way rotation,
 *   `((+0x1E) & 3) * 4 + 2`.
 *
 * A full pool just skips the shot (0x8ED6) without touching the countdown.
 */
function fireWideGun(pool, s, b, ctx) {
  s[b + 0x1c] = (s[b + 0x1c] - 1) & 0xff;
  if (s[b + 0x1c] !== 0) return;
  s[b + 0x1c] = s[b + 0x1d]; // 0x8ECD reload, possibly overridden below

  const child = pool.allocEntitySlot();
  if (child < 0) return; // 0x8ED6: no slot, and the reload already happened
  const type = s[b] & 0x7f;
  let childType;
  let dir;

  if (type === 84) {
    s[b + 0x1c] = 0x0a;
    s[b + 0x1e] = (s[b + 0x1e] + 1) & 0xff;
    dir = (s[b + 0x1e] * 2) & 0x0f;
    childType = 0x26; // type 38
  } else if (type === 86) {
    s[b + 0x1c] = 0x08;
    s[b + 0x1e] = (s[b + 0x1e] + 1) & 0xff;
    dir = ((s[b + 0x1e] & 0x03) * 4 + 2) & 0xff;
    childType = 0x15; // type 21
  } else {
    // 0x8EFC: which side is the player on, and is the terrain moving?
    const playerRight = s[0x02] >= s[b + 0x02];
    const moving = ctx.scroll.speed !== 0;
    dir = playerRight ? (moving ? 0x01 : 0x00) : moving ? 0x07 : 0x08;
    childType = 0x15;
  }

  const cb = child * ENTITY_STRIDE;
  s[cb] = childType; // 0x8DDB spawn_child_at_parent
  s[cb + 0x1a] = dir;
  s[cb + 0x01] = s[b + 0x01];
  s[cb + 0x02] = s[b + 0x02];
}

/** `ground_gun_param_table` (0x8189): 5 x 4 bytes, one per type PAIR. */
const GROUND_GUN_TABLE = 0x8189;

/**
 * The **ground-gun family**, entity types 46-55 — ten types on one handler
 * (0x8094), which makes it the single densest entry in `entity_jump_table`.
 *
 * Each *pair* of types shares a 4-byte parameter row indexed
 * `((type - 0x2E) & 0xFE) * 2`: `[flags, colour, fire period, projectile
 * type]`. The flags byte in +0x05 picks the firing discipline:
 *
 * - **bit 6** — ambush. It holds fire until the player's Y crosses its own,
 *   then shoots once; bit 7 latches the edge so it re-arms only when the
 *   player drops back below.
 * - **bit 5** — sweeper. Its direction counter steps by +0x17 each shot and
 *   it *stops moving* between shots, resuming when the sweep wraps to 4.
 * - neither — a plain turret on a fixed period.
 *
 * The side it enters from is another refresh-register coin flip, and it sets
 * both the entry X and the direction-step sign.
 */
function runGroundGun(pool, slot, ctx, type) {
  const s = pool.slots;
  const b = slot * ENTITY_STRIDE;
  const rom = ctx.rom;

  if ((s[b] & 0x80) === 0) {
    const entry = GROUND_GUN_TABLE + (((type - 0x2e) & 0xfe) << 1);
    // 0x80A9: left side steps +1 from 0, right side steps -1 from 8.
    let bReg = 0x30;
    let d = 0x00;
    let e = 0x01;
    if (prng() & 1) {
      bReg = 0xc0;
      d = 0x08;
      e = 0xff;
    }
    s[b + 0x02] = bReg;
    s[b + 0x0c] = 0x01; // Y motion only
    s[b + 0x08] = 0x50;
    s[b + 0x09] = 0x01; // vy = +1.31
    s[b + 0x03] = 0x48;
    const flags = rom.byte(entry);
    s[b + 0x05] = flags;
    if (flags & 0x20) {
      // 0x80D4: a sweeper ignores the entry X for its step and starts at 0x0C.
      bReg = e;
      d = 0x0c;
    }
    s[b + 0x1d] = d; // direction counter
    s[b + 0x17] = bReg; // direction step
    s[b + 0x04] = rom.byte(entry + 1);
    s[b + 0x1e] = rom.byte(entry + 2);
    s[b + 0x18] = rom.byte(entry + 2);
    s[b + 0x1f] = rom.byte(entry + 3);
    const child = spawnColMarker(pool, s, b);
    if (child < 0) {
      pool.clear(slot);
      return false;
    }
    s[child * ENTITY_STRIDE + 0x03] = 0x50;
    s[b] |= 0x80;
  }

  if (s[b + 0x05] & 0x40) {
    // 0x80FE ambush: edge-triggered on the player crossing this row.
    const playerAbove = s[0x01] < s[b + 0x01];
    if (s[b + 0x05] & 0x80) {
      if (!playerAbove) s[b + 0x05] &= ~0x80; // re-arm
    } else if (playerAbove) {
      fireGroundProjectile(pool, s, b, ctx);
      s[b + 0x05] |= 0x80;
    }
  } else {
    // 0x811D: the periodic turret.
    s[b + 0x18] = (s[b + 0x18] - 1) & 0xff;
    if (s[b + 0x18] === 0) {
      s[b + 0x18] = s[b + 0x1e];
      s[b + 0x1d] = (s[b + 0x1d] + s[b + 0x17]) & 0x0f;
      fireGroundProjectile(pool, s, b, ctx);
      if (s[b + 0x05] & 0x20) {
        if (s[b + 0x1d] === 0x04) {
          // 0x814D: the sweep wrapped - restart it and start moving again.
          s[b + 0x1d] = 0x0c;
          s[b + 0x0c] = 0x01;
          s[b + 0x03] = 0x48;
          s[s[b + 0x1b] * ENTITY_STRIDE + 0x03] = 0x50;
        } else {
          s[b + 0x18] = 0x01; // fire again next frame
          s[b + 0x0c] = 0x00; // and hold station while sweeping
        }
      }
    }
  }
  return true;
}

/** `fire_ground_projectile` (0x816D). */
function fireGroundProjectile(pool, s, b, ctx) {
  s[b + 0x03] = 0x4c; // muzzle-flash sprite for this frame
  s[s[b + 0x1b] * ENTITY_STRIDE + 0x03] = 0x54;
  const child = pool.allocEntitySlot();
  if (child < 0) return;
  const cb = child * ENTITY_STRIDE;
  s[cb] = s[b + 0x1f]; // projectile type from the parameter row
  s[cb + 0x1a] = s[b + 0x1d]; // direction
  s[cb + 0x01] = s[b + 0x01];
  s[cb + 0x02] = s[b + 0x02];
  void ctx;
}

/**
 * **Type 36**, the flashing descender (0x8296). Drifts down at half a pixel
 * per frame, colour strobing by XOR 0x0E, and soaks **sixteen** shots through
 * the shared box hit-sub before it finally dies.
 */
function runFlashing(pool, slot, ctx) {
  const s = pool.slots;
  const b = slot * ENTITY_STRIDE;
  if ((s[b] & 0x80) === 0) {
    randomXPos(s, b);
    s[b + 0x0c] = 0x01;
    s[b + 0x08] = 0x80; // vy = +0.5
    s[b + 0x03] = 0x34;
    s[b + 0x04] = 0x8f;
    s[b + 0x19] = 0x10;
    s[b] |= 0x80;
  }
  s[b + 0x04] ^= 0x0e; // 0x829C
  // 0x82AC entity_post + 0x82AF the box hit-sub: each hit decrements +0x19,
  // rumbles, and undoes the death remap until the count runs out.
  if (ctx) {
    const hit = checkEntityCollisions(pool, ctx.rom, slot, ctx.player.fireMode);
    if (hit) {
      if (hit.hitBy === 0) {
        collisionResponse(pool, ctx.rom, slot, 0);
        return false;
      }
      pool.clear(hit.hitBy);
      s[b + 0x19] = (s[b + 0x19] - 1) & 0xff;
      if (s[b + 0x19] === 0) {
        s[b + 0x18] = 36;
        s[b] = 0x23;
        return false;
      }
      ctx.sound.playEvent(0x14);
    }
  }
  return true;
}

/**
 * **Type 64**, the proto-structure (0x8279): not an enemy at all but a
 * **re-roll** - every frame it replaces its own type with an entry from the
 * flat spawn list, indexed by half the encounter counter plus a small random
 * kick. The higher the difficulty, the nastier the substitute.
 */
function runProtoStructure(pool, slot, ctx) {
  const s = pool.slots;
  const b = slot * ENTITY_STRIDE;
  let idx = ((ctx && ctx.spawn ? ctx.spawn.encounter : 0) >> 1) + (prng() & 3);
  if (idx >= 0x60) idx = 0x5f; // 0x8284
  s[b] = ctx.rom.byte(0xbecc + idx);
  return false;
}

/**
 * **Type 9** (0x79FB -> 0x7A04): the missile umber. Same weaving body as
 * types 7/8 but in light green (sprite 0xE0 / marker 0xE8), and every eight
 * frames it drops a **type-20 homing bullet** at its own position - the
 * steady missile stream players remember from round 1.
 */
const UMBER9_FIRE_PERIOD = 0x08;

/**
 * The **stealth pair**, types 30/32 with their live halves 31/33
 * (0x7E9C / 0x7F84). Type 30 spawns TWO entities: itself at X=0x30 falling
 * down-right and a mirror child at X=0xC0 (sprite 0xF0) drifting left, the
 * child a real entity of type+1. Type 32 is the same from the bottom edge
 * moving up (bit 6 flips the Y comparison).
 *
 * When the player's Y crosses theirs, both halves stop falling and slide
 * horizontally toward each other (bflags 2); once they close within 11
 * pixels they **merge** - the parent becomes the wide sprite 0xF4, the child
 * despawns - and the merged body sails on. An orphaned parent (its partner
 * shot) bumps its own type by one and carries on as the solo tracker.
 * Both halves strobe their colour by XOR 6 every frame.
 */
function runStealthPair(pool, slot, ctx, type) {
  const s = pool.slots;
  const b = slot * ENTITY_STRIDE;

  if ((s[b] & 0x80) === 0) {
    const child = pool.allocEntitySlot();
    if (child < 0) {
      pool.clear(slot);
      return false;
    }
    pool.clear(child);
    s[b + 0x1b] = child;
    s[b + 0x0c] = 0x01;
    s[b + 0x08] = 0x80;
    s[b + 0x09] = 0x01; // vy = +1.5
    s[b + 0x0a] = 0x80;
    s[b + 0x0b] = 0x01; // vx = +1.5 (only used once bflags gains bit 1)
    s[b + 0x02] = 0x30;
    s[b + 0x03] = 0xec;
    s[b + 0x04] = 0x8f;
    s[b + 0x05] &= ~0x40;
    if (type === 32) {
      // 0x7ED1: the bottom-edge variant rises instead.
      s[b + 0x05] |= 0x40;
      s[b + 0x08] = 0x00;
      s[b + 0x09] = 0xff;
      s[b + 0x01] = 0xd0;
    }
    // 0x7EE9: thirteen bytes of the parent are copied into the child, then
    // the mirror fields overwrite position and velocity.
    const cb = child * ENTITY_STRIDE;
    for (let i = 0; i < 0x0d; i++) s[cb + i] = s[b + i];
    s[cb + 0x03] = 0xf0;
    s[cb + 0x02] = 0xc0;
    s[cb + 0x0a] = 0x80;
    s[cb + 0x0b] = 0xfe; // vx = -1.5
    s[cb] = type + 1; // the live half: 31 or 33
    s[b] |= 0x80;
    if (type === 30) {
      // 0x7F11: the diagonal pair actually drops the fractions.
      s[b + 0x0a] = 0x00;
      s[cb + 0x0a] = 0x00;
      s[cb + 0x0b] = 0xff; // child vx = -1.0
    }
    s[cb] |= 0x80;
    return stealthBlink(pool, s, b, ctx);
  }

  if ((s[b + 0x05] & 0x80) === 0) {
    const child = s[b + 0x1b];
    const cb = child * ENTITY_STRIDE;
    if ((s[cb] & 0x7f) !== type + 1) {
      // 0x7F81: the partner is gone - become the solo tracker.
      s[b] = ((s[b] & 0x7f) + 1) | 0x80;
      return runStealthTracker(pool, slot, ctx);
    }
    // 0x7F3A: has the player's row been crossed? (inverted for the riser)
    const crossed =
      s[b + 0x05] & 0x40 ? s[0x01] >= s[b + 0x01] : s[0x01] < s[b + 0x01];
    if (crossed) {
      s[b + 0x0c] = 0x02; // both halves: X motion only, converge
      s[cb + 0x0c] = 0x02;
    }
    const gap = (s[cb + 0x02] - s[b + 0x02]) & 0xff;
    if (gap < 0x0b) {
      // 0x7F5B: MERGE. The parent widens, the child despawns.
      s[b + 0x05] |= 0x80;
      s[b + 0x03] = 0xf4;
      s[cb] = 0x28;
      s[b + 0x02] = (s[b + 0x02] + 5) & 0xff;
      s[b + 0x0c] = 0x01;
    }
  }
  return stealthBlink(pool, s, b, ctx);
}

/** Types 31/33 on their own (0x7F84): stop falling once the row is crossed. */
function runStealthTracker(pool, slot, ctx) {
  const s = pool.slots;
  const b = slot * ENTITY_STRIDE;
  if ((s[b] & 0x80) === 0) s[b] |= 0x80;
  const crossed =
    s[b + 0x05] & 0x40 ? s[0x01] >= s[b + 0x01] : s[0x01] < s[b + 0x01];
  if (crossed) s[b + 0x0c] = 0x02;
  return stealthBlink(pool, s, b, ctx);
}

/** 0x7F73: the shared strobe + update + post tail. */
function stealthBlink(pool, s, b, ctx) {
  s[b + 0x04] ^= 0x06;
  void pool;
  void ctx;
  return true;
}

/** Burster tables (0x807C / 0x8084 / 0x8087 / 0x808A). */
const BURSTER_ENTRY_TABLE = 0x807c;
const BURSTER_DIRS_ABOVE = 0x8084;
const BURSTER_DIRS_BELOW = 0x8087;
const BURSTER_SPREAD_OFFSETS = 0x808a;

/**
 * The **bursters**, types 34 / 65 / 66 (0x7F99). One of four scripted entry
 * points (X and initial direction from 0x807C, picked by R&6), then a
 * periodic burst:
 *
 * - **34** (grey 0x88): every 0x30 frames, three type-38 fragments along the
 *   3-direction list for whichever side the player is on. 7 HP.
 * - **65** (blue 0x85): every 0x20 frames, one type-20 homing bullet. 4 HP.
 * - **66** (yellow 0x8B): every 0x30 frames, SFX 0x15 and **five type-59
 *   darts**, all aimed at the player, placed at the five [dy, dx] offsets of
 *   0x808A - a tight aimed shotgun.
 */
function runBurster(pool, slot, ctx, type) {
  const s = pool.slots;
  const b = slot * ENTITY_STRIDE;
  const rom = ctx.rom;

  if ((s[b] & 0x80) === 0) {
    const child = spawnColMarker(pool, s, b);
    if (child < 0) {
      pool.clear(slot);
      return false;
    }
    s[child * ENTITY_STRIDE + 0x03] = 0xd0;
    const e = BURSTER_ENTRY_TABLE + (prng() & 6);
    s[b + 0x17] = 0x01;
    s[b + 0x02] = rom.byte(e);
    setVelocityFromDir(s, b, rom, rom.byte(e + 1) & 0x0f, s[b + 0x17]);
    s[b + 0x0c] = 0x03;
    s[b + 0x03] = 0xcc;
    s[b + 0x04] = 0x88;
    s[b + 0x0d] = 0x30; // period
    s[b + 0x1d] = 0x30; // countdown
    s[b + 0x1e] = 0x03; // burst size
    s[b + 0x1f] = 0x26; // projectile type 38
    s[b + 0x19] = 0x07; // HP
    s[b] |= 0x80;
    if (type === 65) {
      s[b + 0x04] = 0x85;
      s[b + 0x0d] = 0x20;
      s[b + 0x1e] = 0x01;
      s[b + 0x1f] = 0x14; // type 20
      s[b + 0x19] = 0x04;
    } else if (type === 66) {
      s[b + 0x04] = 0x8b;
      s[b + 0x1e] = 0x05;
      s[b + 0x1f] = 0x3b; // type 59
      s[b + 0x05] |= 0x01; // the aimed-spread mode
    }
  }

  s[b + 0x1d] = (s[b + 0x1d] - 1) & 0xff;
  if (s[b + 0x1d] === 0) {
    s[b + 0x1d] = s[b + 0x0d];
    let table;
    let aimDir = 0;
    const aimed = (s[b + 0x05] & 0x01) !== 0;
    if (aimed) {
      ctx.sound.playEvent(0x15); // 0x8023
      aimDir = aimDirection(pool, rom, b);
      table = BURSTER_SPREAD_OFFSETS;
    } else {
      table = s[0x01] >= s[b + 0x01] ? BURSTER_DIRS_BELOW : BURSTER_DIRS_ABOVE;
    }
    let tp = table;
    for (let i = 0; i < s[b + 0x1e]; i++) {
      const q = pool.allocEntitySlot();
      if (q < 0) break;
      const qb = q * ENTITY_STRIDE;
      s[qb] = s[b + 0x1f];
      let y = s[b + 0x01];
      let x = s[b + 0x02];
      let dir;
      if (aimed) {
        y = (y + rom.sbyte(tp)) & 0xff;
        x = (x + rom.sbyte(tp + 1)) & 0xff;
        tp += 2;
        dir = aimDir;
      } else {
        dir = rom.byte(tp);
        tp += 1;
      }
      s[qb + 0x01] = y;
      s[qb + 0x02] = x;
      s[qb + 0x1a] = dir & 0xff;
    }
  }
  return true;
}

/**
 * **Type 67** (0x839F): the phase charger. It materialises at a random spot
 * and *hangs there* flickering (sprite 0x20 <-> 0x14, colour 0x86 <-> 0x8A,
 * both XORed every frame) without even moving; after 0x78 frames it turns
 * red-white (0x8D), charges straight at the player at speed 3, then picks a
 * fresh random dwell (R & 0x1E + 0x32) and repeats - 0x1E charges in all.
 * The fire weapon kills it outright; shots it soaks five of (0x8432).
 */
function runPhaseCharger(pool, slot, ctx) {
  const s = pool.slots;
  const b = slot * ENTITY_STRIDE;
  const rom = ctx.rom;

  if ((s[b] & 0x80) === 0) {
    const r = prng();
    s[b + 0x01] = ((r & 0x7f) + 0x10) & 0xff;
    s[b + 0x02] = (((r >> 8) & 0x7f) + 0x40) & 0xff;
    s[b + 0x04] = 0x86;
    s[b + 0x03] = 0x20;
    s[b + 0x0c] = 0x03;
    s[b + 0x19] = 0x05; // shot soak
    s[b + 0x17] = 0x03; // charge speed
    s[b + 0x1b] = 0x78; // dwell
    s[b + 0x1c] = 0x1e; // charges left
    s[b] |= 0x80;
  }

  s[b + 0x03] ^= 0x34; // 0x83D8: the flicker
  s[b + 0x04] ^= 0x0c;

  s[b + 0x1b] = (s[b + 0x1b] - 1) & 0xff;
  if (s[b + 0x1b] === 0) {
    s[b + 0x05] |= 0x01; // 0x83F7: armed - starts moving from here on
    s[b + 0x1c] = (s[b + 0x1c] - 1) & 0xff;
    if (s[b + 0x1c] === 0) s[b + 0x05] |= 0x02; // out of charges: drift on
    if ((s[b + 0x05] & 0x02) === 0) {
      s[b + 0x04] = 0x8d; // 0x840A: the charge flash
      s[b + 0x1b] = (prng() & 0x1e) + 0x32;
      aimAtPlayer(pool, rom, b); // 0x8417 aim + apply at +0x17
    }
  }

  // 0x83EE: before the first charge it does not move at all - SAT write only.
  const moving = (s[b + 0x05] & 0x01) !== 0;

  // 0x841D entity_post, with the custom soak tail at 0x8420.
  const hit = checkEntityCollisions(pool, rom, slot, ctx.player.fireMode);
  if (hit) {
    if (hit.hitBy === 0) {
      collisionResponse(pool, rom, slot, 0);
      return false;
    }
    if (hit.hitBy === 4) {
      // 0x842A: the fire weapon bypasses the soak entirely.
      s[b + 0x18] = 67;
      s[b] = 0x23;
      return false;
    }
    pool.clear(hit.hitBy);
    s[b + 0x19] = (s[b + 0x19] - 1) & 0xff;
    if (s[b + 0x19] === 0) {
      s[b + 0x18] = 67;
      s[b] = 0x23;
      return false;
    }
    ctx.sound.playEvent(0x14); // 0x8436
  }
  return moving;
}

/** The 1-UP's two sprite frames (0x876B / 0x878B), 32 bytes each. */
const ONE_UP_FRAMES = 0x876b;

/**
 * **Type 62** (0x8709): the 1-UP. The invisible riser the type-61 walker's
 * kill lottery leaves behind - it floats up at 1.5 px/frame wearing **sprite
 * pattern 0**, whose 32 bytes it re-uploads from ROM every 16 frames,
 * flip-flopping between two frames (the pulsing wing badge). Touching it
 * restores the ship, **adds a life**, plays SFX 8 and refreshes the panel.
 */
function runOneUp(pool, slot, ctx) {
  const s = pool.slots;
  const b = slot * ENTITY_STRIDE;

  if ((s[b] & 0x80) === 0) {
    s[b + 0x09] = 0xff;
    s[b + 0x08] = 0x80; // vy = -1.5
    s[b + 0x03] = 0x00; // sprite pattern 0 - animated below
    s[b + 0x04] = 0x87;
    s[b + 0x0c] = 0x01;
    s[b] |= 0x80;
    return true;
  }

  // 0x8728: every 16 frames LDIRVM one of the two frames into VRAM 0x1800.
  const counter = s[b + 0x0d];
  s[b + 0x0d] = (counter + 1) & 0xff;
  if ((counter & 0x0f) === 0 && ctx.screen) {
    const src = ONE_UP_FRAMES + ((counter & 0x10) << 1);
    ctx.screen.spriteGen.set(ctx.rom.slice(src, 0x20), 0);
  }

  // 0x8752: player-only collision (0x44B0).
  if (ctx && playerTouches(pool, ctx.rom, slot)) {
    ctx.state.lives = (ctx.state.lives + 1) & 0xff; // 0x8762: INC (0xE10A)
    ctx.sound.playEvent(0x08);
    pool.clear(slot);
    return false;
  }
  return true;
}

/** `base_spawner_spawn_table` (0x7AF7): 8 x (enemy type, count). */
const WAVE_SPAWN_TABLE = 0x7af7;

/**
 * `inc_encounter_inner` (0xBFCB) reached through `SUB_bfc8` (0xBFC8): 0xE130
 * saturates at 0xFF and does not move at all while a base encounter is active
 * (0xBFCE tests 0xE150 bit 1) - the base owns the difficulty curve while it
 * is on screen.
 */
export function incEncounter(ctx) {
  if (!ctx.spawn) return;
  if (ctx.base && ctx.base.flags & 0x02) return;
  if (ctx.spawn.encounter < 0xff) ctx.spawn.encounter++;
}

/** `dec_encounter_b` (0xBFBF): saturating decrement of 0xE130. */
export function decEncounter(ctx) {
  if (!ctx.spawn) return;
  if (ctx.spawn.encounter > 0) ctx.spawn.encounter--;
}

/**
 * The enemy-wave spawner, types 11 and 69.
 *
 * `handler_type11_base_spawner` (0x7AD4) is a one-shot: it reads the encounter
 * counter 0xE130, takes `((E130 >> 4) & 7) * 2` as an index into
 * `base_spawner_spawn_table` (0x7AF7) - pairs of **(enemy type, count)**, not
 * the Y/X positions the KB used to claim - loads them, sets a 40-frame
 * interval, and jumps straight into the type-69 body in the same frame.
 *
 * `base_spawner_active` (0x7A67) is then an invisible emitter: it pushes no
 * sprite and takes no collisions. It picks a random column, walks it +/-2 per
 * shot (bouncing off both edges through the unsigned `CP 0xC0` test at
 * 0x7AC8, which catches the left edge via 8-bit wrap too), and every 40
 * ungated frames drops one child of the chosen type at its current X, Y = 0,
 * until the count runs out and it retires.
 */
function runWaveSpawner(pool, slot, ctx) {
  const s = pool.slots;
  const b = slot * ENTITY_STRIDE;

  if ((s[b] & 0x7f) === 11) {
    // 0x7AD4: pick the wave, become type 69, then fall through.
    const idx = (((ctx && ctx.spawn ? ctx.spawn.encounter : 0) >> 4) & 7) * 2;
    s[b] = 0x45;
    s[b + 0x01] = ctx.rom.byte(WAVE_SPAWN_TABLE + idx);
    s[b + 0x02] = ctx.rom.byte(WAVE_SPAWN_TABLE + idx + 1);
    s[b + 0x03] = 0x28;
  }

  if ((s[b] & 0x80) === 0) {
    // 0x7A67 init: latch type/count/interval, then scatter to a random column.
    s[b + 0x18] = s[b + 0x01];
    s[b + 0x19] = s[b + 0x02];
    s[b + 0x1c] = s[b + 0x03];
    s[b + 0x1b] = s[b + 0x03];
    randomXPos(s, b);
    // 0x7A85: the half of the screen decides the walk direction and the
    // child's +0x1A parameter together.
    if (s[b + 0x02] < 0x78) {
      s[b + 0x0a] = 0x02;
      s[b + 0x1a] = 0x03;
    } else {
      s[b + 0x0a] = 0xfe;
      s[b + 0x1a] = 0x05;
    }
    s[b] |= 0x80;
  }

  if (ctx && ctx.spawn && ctx.spawn.ctrl & 0x08) return false; // 0x7A9C gate
  s[b + 0x1b] = (s[b + 0x1b] - 1) & 0xff;
  if (s[b + 0x1b] !== 0) return false;
  s[b + 0x1b] = s[b + 0x1c]; // 0x7AA6: reload before the alloc attempt

  const child = pool.allocEntitySlot();
  if (child < 0) return false; // 0x7AAF: pool full - no ammo lost, retry later
  // 0x8DDB writes only these four fields; the rest of the slot keeps whatever
  // the previous occupant left, exactly as the ROM does.
  const cb = child * ENTITY_STRIDE;
  s[cb] = s[b + 0x18];
  s[cb + 0x1a] = s[b + 0x1a];
  s[cb + 0x01] = s[b + 0x01];
  s[cb + 0x02] = s[b + 0x02];

  s[b + 0x19] = (s[b + 0x19] - 1) & 0xff;
  if (s[b + 0x19] === 0) {
    pool.clear(slot); // 0x7ABC: out of ammo, retire
    return false;
  }
  s[b + 0x02] = (s[b + 0x02] + s[b + 0x0a]) & 0xff;
  if (s[b + 0x02] >= 0xc0) s[b + 0x0a] = -s[b + 0x0a] & 0xff; // 0x7ACB
  return false;
}

/** `explode_enemies` (0x8A26) - shared with fire 6's expire path. */
function fireExplodeEnemies(ctx) {
  const s = ctx.pool.slots;
  for (let q = 5; q <= 25; q++) {
    const type = ctx.pool.type(q);
    if (type === 0 || type === 39 || type === 63 || type === 72 || type === 83) continue;
    s[q * ENTITY_STRIDE + 0x18] = type;
    s[q * ENTITY_STRIDE] = 35;
  }
}

/** Type 44 (main attacker) and its complement child, type 39. */
const TYPE_MAIN_ATTACKER = 44;
const TYPE_COL_MARKER = 39;
/** plane_compl pattern (entity-sprite-mapping row 44). */
const COMPLEMENT_PATTERN = 0x44;

/**
 * `handler_type44` (0x82D0): allocate the type-39 complement child (or die -
 * spawn_col_marker's failure path clears the parent), pick a random column,
 * speed 1-4, then **aim at the player** (0x4C8B) - which is where the velocity
 * the init itself never writes comes from.
 */
function runType44(pool, slot, ctx) {
  const s = pool.slots;
  const b = slot * ENTITY_STRIDE;
  if ((s[b] & 0x80) === 0) {
    const child = pool.allocEntitySlot();
    if (child < 0) {
      pool.clear(slot);
      return false;
    }
    pool.clear(child);
    const cb = child * ENTITY_STRIDE;
    s[cb] = TYPE_COL_MARKER;
    s[cb + 0x03] = COMPLEMENT_PATTERN;
    s[cb + 0x04] = 0x81;
    s[cb + 0x18] = 2;
    s[b + 0x1b] = child;

    randomXPos(s, b);
    s[b + 0x17] = (prng() & 3) + 1;
    s[b + 0x0c] = 0x03;
    s[b + 0x03] = 0x40; // plane
    s[b + 0x04] = 0x83;
    if (ctx) aimAtPlayer(pool, ctx.rom, b); // 0x82E6, at the +0x17 speed above
    s[b] |= 0x80;
  }
  return true;
}

/**
 * 0x71F6, run after `entity_update`: draw the complement sprite at the
 * parent's position using the child's pattern/colour, and refresh the child's
 * keepalive (+0x18) to 2.
 */
export function postTypeHandler(pool, slot) {
  const s = pool.slots;
  const b = slot * ENTITY_STRIDE;
  const type = s[b] & 0x7f;
  const hasChild =
    type === TYPE_MAIN_ATTACKER ||
    (type >= 12 && type <= 15) ||
    (type >= 4 && type <= 6) ||
    (type >= 16 && type <= 18) ||
    type === 7 ||
    type === 8 ||
    type === 61 || // 0x8365: the walker calls 0x71F6 too
    (type >= 22 && type <= 29) || // veybar + edge swoopers (0x7D86 / 0x7E58)
    (type >= 46 && type <= 55) || // ground guns (0x8167)
    type === 10 || // the duster (0x79B1)
    type === 57 || type === 58 || // the paired descenders carry complements
    type === 34 || type === 65 || type === 66; // bursters (0x8076)
  if (!hasChild || (s[b] & 0x80) === 0) return;
  const child = s[b + 0x1b];
  const cb = child * ENTITY_STRIDE;
  if ((s[cb] & 0x7f) !== TYPE_COL_MARKER) return;
  if (s[b + 0x01] !== 0) {
    pool.pushSprite(s[b + 0x01] - 0x11, s[b + 0x02], s[cb + 0x03], s[cb + 0x04]);
  }
  s[cb + 0x18] = 2;
}

/**
 * `handler_type60` (0x869E): the player death sequence, run on slot 0 after
 * `collision_response` remaps type 1 -> 60.
 *
 * Init (bit 7 clear):
 *   - if the spawn-invincibility flag (+0x05 bit 7) is still set, the hit is
 *     shrugged off: the type byte reverts to 0x81 and the ship handler runs
 *     as if nothing happened (0x86AA)
 *   - otherwise: fire_reset, **halve both ALC accumulators** (SRL 0xE132 /
 *     SRL 0xE12E at 0x86B4 - dying eases the difficulty), SFX event 16, and
 *     an 11-frame animate-only cycle from the table at 0x86F3
 * When the frame counter wraps to 0 (0x86E4): raise the player-hit flag
 * (0xE102 bit 0) and clear slot 0; `player_hit_handler` (0x4649) then
 * decrements the lives counter and picks respawn or game over.
 *
 * @returns {'revert'|'animating'|'dead'}
 */
const PLAYER_DEATH_ANIM_TABLE = 0x86f3;
const PLAYER_DEATH_SFX = 0x10;

export function runPlayerDeath(ctx) {
  const s = ctx.pool.slots;
  if ((s[0] & 0x80) === 0) {
    if (s[0x05] & 0x80) {
      s[0] = 0x81; // invincible: cancel the death outright
      return 'revert';
    }
    fireSelect(ctx.player, ctx.rom, 0, ctx); // 0x86B1: fire_reset on death
    if (ctx.spawn) {
      ctx.spawn.posBias >>= 1; // 0x86B4: SRL 0xE132
      ctx.spawn.accHi >>= 1; // 0x86B9: SRL 0xE12E
    }
    ctx.sound.playEvent(PLAYER_DEATH_SFX);
    s[0x0d] = 0x04;
    s[0x0e] = 0x04;
    s[0x0f] = 0x01;
    s[0x10] = 0x0b;
    s[0x11] = PLAYER_DEATH_ANIM_TABLE & 0xff;
    s[0x12] = PLAYER_DEATH_ANIM_TABLE >> 8;
    s[0x0c] = 0x04; // animate only
    s[0] |= 0x80;
  }
  if (s[0x0f] === 0) {
    ctx.pool.clear(0);
    return 'dead'; // 0x86EB: SET 0,(0xE102)
  }
  return 'animating';
}

/** One-time setup once a structure has entered the playfield. */
function initWideStructure(s, b) {
  s[b + 0x03] = WIDE_STRUCTURE_INIT.satName;
  s[b + 0x04] = WIDE_STRUCTURE_INIT.satColor;
  s[b + 0x0c] = WIDE_STRUCTURE_INIT.behaviour;
  s[b + 0x19] = WIDE_STRUCTURE_INIT.field19;
  s[b + 0x1c] = WIDE_STRUCTURE_INIT.childHi;
  s[b + 0x1d] = WIDE_STRUCTURE_INIT.colWidth;
}

export { WIDE_STRUCTURE_TYPES };
