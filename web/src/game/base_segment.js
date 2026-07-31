/**
 * `handler_type73_base_segment` (0x8A5A) and its four helpers — the
 * destructible parts a base is built from (entity types 73-79 / 0xC9-0xCF).
 *
 * A segment is placed as a normal ground structure and scrolls down with the
 * terrain until two gates open: 0xE700 bit 1 (the row actually scrolled) and
 * 0xE150 bit 1 (the base controller opened the encounter). Only then does it
 * take its parameters from `base_segment_table` (0x8DF1) and start running.
 *
 * While active it walks a four-phase animation whose dwell times come from a
 * per-segment **attack pattern** (0x93AB, assigned round-robin by the
 * controller), draws itself straight into VRAM through a per-type tile
 * blitter, and every time its 0x14/0x15 accumulator carries it spits out
 * projectiles - each type with its own firing geometry, up to the core's
 * player-aimed five-way fan.
 */

import { ENTITY_STRIDE } from './state.js';
import { aimDirection } from './player.js';
import { checkEntityCollisions, collisionResponse } from './collision.js';

/** `base_segment_table` (0x8DF1): 7 x (sat, HP, y_off, x_off, rate). */
const BASE_SEGMENT_TABLE = 0x8df1;
// The two jump tables the ROM dispatches through (0x8C1D for drawing,
// 0x8D1C for firing) are unrolled into the switches below; their targets are
// noted per case so the asm stays greppable.
/** The core's aimed-fan direction deltas (0x8DB3): 0, -1, +1, -2, +2. */
const FAN_DELTAS = 0x8db3;

/** Per-type wreck tile blocks, selected by the segment's shape id (+0x18). */
const WRECK_BLOCKS = { 0x4b: 0x8ce1, 0x4c: 0x8ce4, 0x4d: 0x8ce8, 0x4e: 0x8cda };
/** The 3x3 core, by remaining HP: healthy / damaged / wrecked. */
const CORE_BLOCKS = [0x8ced, 0x8cfa, 0x8d07];

/**
 * `base_pattern_load_record` (0x8BF5): pull the next 3-byte record out of the
 * segment's attack pattern into the phase dwell rates, looping back to the
 * pattern's start on the 0x00 terminator.
 */
function loadPatternRecord(s, b, rom, hl) {
  if (rom.byte(hl) === 0) hl = s[b + 0x0f] | (s[b + 0x10] << 8); // 0x8BF9
  s[b + 0x09] = rom.byte(hl);
  s[b + 0x0a] = rom.byte((hl + 1) & 0xffff);
  s[b + 0x0b] = rom.byte((hl + 2) & 0xffff);
  const next = (hl + 3) & 0xffff;
  s[b + 0x11] = next & 0xff;
  s[b + 0x12] = next >> 8;
}

/**
 * `base_segment_draw` (0x8C15): blit the segment at its current animation
 * phase. Every type but the core writes a small block of consecutive tile
 * codes; the shapes differ only in row count, column count and whether the
 * tile index advances (0x8C2D is shared by all of them).
 *
 * @param {number} type 73-79
 */
function drawSegment(ctx, s, b, type) {
  const { rom, screen, scroll } = ctx;
  const phase = s[b + 0x0c];
  let first;
  let rows;
  let cols;
  let step;

  switch (type) {
    case 73: // 0x8C2B
      first = (0xd3 + 4 * phase) & 0xff;
      rows = 2;
      cols = 2;
      step = 1;
      break;
    case 74: // 0x8C5E
      first = (0xc3 + 4 * phase) & 0xff;
      rows = 2;
      cols = 2;
      step = 1;
      break;
    case 75: // 0x8C62
      first = (0xbf + phase) & 0xff;
      rows = 1;
      cols = 1;
      step = 0;
      break;
    case 76: // 0x8C70
      first = (0xbf + phase) & 0xff;
      rows = 1;
      cols = 2;
      step = 0;
      break;
    case 77: // 0x8C76
      first = (0xbf + phase) & 0xff;
      rows = 2;
      cols = 1;
      step = 0;
      break;
    case 78: // 0x8C7C
      first = (0xbf + phase) & 0xff;
      rows = 2;
      cols = 2;
      step = 0;
      break;
    default: {
      // 0x8C80: the core picks one of three 3x3 blocks by remaining HP.
      const hp = s[b + 0x19];
      const block = hp >= 0x15 ? CORE_BLOCKS[0] : hp !== 0 ? CORE_BLOCKS[1] : CORE_BLOCKS[2];
      drawTileBlock(ctx, block, s[b + 0x02] - 0x24, s[b + 0x01] - 0x14);
      return;
    }
  }

  // 0x8C39: the VRAM address was resolved once at activation into +0x06/07.
  const addr = s[b + 0x06] | (s[b + 0x07] << 8);
  let tile = first;
  for (let r = 0; r < rows; r++) {
    const cell = addr - 0x3800 + r * 0x20;
    for (let c = 0; c < cols; c++) {
      const row = (cell / 32) | 0;
      const col = (cell % 32) + c;
      if (row >= 0 && row < 24 && col >= 0 && col < 24) {
        screen.nameTable[row * 32 + col] = tile;
        scroll.ring[((scroll.ringRow + row) % 24) * 24 + col] = tile;
      }
      tile = (tile + step) & 0xff;
    }
  }
  void rom;
}

/**
 * `draw_tile_block` (0x88ED) as the base uses it: stamp `[rows]([len]tiles)`
 * into both the name table and the scroll ring, from a pixel coordinate.
 */
function drawTileBlock(ctx, block, xPx, yPx) {
  const { rom, screen, scroll } = ctx;
  let a = block;
  const rows = rom.byte(a++);
  const col0 = (xPx & 0xff) >> 3;
  const row0 = (yPx & 0xff) >> 3;
  for (let r = 0; r < rows; r++) {
    const len = rom.byte(a++);
    for (let i = 0; i < len; i++) {
      const tile = rom.byte(a++);
      const row = row0 + r;
      const col = col0 + i;
      if (row >= 0 && row < 24 && col >= 0 && col < 24) {
        screen.nameTable[row * 32 + col] = tile;
        scroll.ring[((scroll.ringRow + row) % 24) * 24 + col] = tile;
      }
    }
  }
}

/**
 * `base_segment_draw_wreck` (0x8CA2): on death, leave the right rubble block
 * for the shape id in +0x18, each with its own pixel offset.
 */
function drawWreck(ctx, s, b) {
  const shape = s[b + 0x18];
  if (shape === 0x4f) {
    // The core redraws its own 3x3 (0x8CB9 jumps into the HP-selected path).
    drawSegment(ctx, s, b, 79);
    return;
  }
  const block = WRECK_BLOCKS[shape] ?? WRECK_BLOCKS[0x4e];
  // 0x8CBE-0x8CD7: 0x4B keeps X-0x1C/Y-0x0C, 0x4C shifts X, 0x4D shifts Y,
  // the default shifts both.
  const x = shape === 0x4b || shape === 0x4d ? s[b + 0x02] - 0x1c : s[b + 0x02] - 0x20;
  const y = shape === 0x4b || shape === 0x4c ? s[b + 0x01] - 0x0c : s[b + 0x01] - 0x10;
  drawTileBlock(ctx, block, x, y);
}

/** `spawn_child_at_parent` (0x8DDB): four fields, nothing else cleared. */
function spawnChild(pool, s, b, type, param) {
  const child = pool.allocEntitySlot();
  if (child < 0) return false;
  const cb = child * ENTITY_STRIDE;
  s[cb] = type;
  s[cb + 0x1a] = param & 0xff;
  s[cb + 0x01] = s[b + 0x01];
  s[cb + 0x02] = s[b + 0x02];
  return true;
}

/**
 * `base_segment_spawn_debris` (0x8D14): the firing geometry, one entry per
 * type. Projectile types are 0x15 (21), 0x2A (42), 0x2B (43) and 0x2D (45);
 * the parameter in +0x1A is a direction code.
 */
function fireSegment(ctx, s, b, type) {
  const { pool, rom } = ctx;
  switch (type) {
    case 73: {
      // 0x8D2A: a rotating direction counter with two escape hatches.
      let a = s[b + 0x13];
      for (;;) {
        a = (a + 3) & 0xff;
        s[b + 0x13] = a;
        const n = a & 0x0f;
        if (n >= 0x0f) {
          spawnChild(pool, s, b, 0x2a, 4); // 0x8D48
          return;
        }
        if (n >= 0x0e) {
          spawnChild(pool, s, b, 0x2a, 4); // 0x8D38 -> the idx2 body
          return;
        }
        if (n >= 0x09) {
          a = n; // 0x8D3C: keep stepping from the masked value
          continue;
        }
        spawnChild(pool, s, b, 0x15, n); // 0x8D40
        return;
      }
    }
    case 74:
    case 77: {
      // 0x8D51 / 0x8D93: a burst of B consecutive directions, wrapping at 9.
      const count = type === 74 ? 4 : 2;
      for (let i = 0; i < count; i++) {
        let c = s[b + 0x13];
        if (c >= 0x09) c = 0;
        if (!spawnChild(pool, s, b, 0x2b, c)) return;
        s[b + 0x13] = (c + 1) & 0xff;
      }
      return;
    }
    case 75:
      spawnChild(pool, s, b, 0x2a, 0); // 0x8D6C
      return;
    case 76: {
      // 0x8D73: a shot and its mirror image, except on the straight-down one.
      s[b + 0x13] = (s[b + 0x13] - 1) & 0xff;
      const c = s[b + 0x13] & 0x07;
      if (c === 4) {
        spawnChild(pool, s, b, 0x2b, 4);
        return;
      }
      if (!spawnChild(pool, s, b, 0x2b, c)) return;
      spawnChild(pool, s, b, 0x2b, (8 - c) & 0xff); // 0x8D8C
      return;
    }
    case 78: {
      // 0x8D98: five shots fanned around the direction of the player.
      // 0x8D98 calls the aim-only 0x4C91: the core must not re-aim itself.
      const dir = aimDirection(pool, rom, b);
      for (let i = 0; i < 5; i++) {
        const delta = rom.sbyte(FAN_DELTAS + i);
        if (!spawnChild(pool, s, b, 0x2b, (delta + dir) & 0xff)) return;
      }
      return;
    }
    default: {
      // 0x8DB8: the core mostly sprays type 0x2D, but every fourth shot is
      // the plain 0x2A of the idx2 body.
      s[b + 0x13] = (s[b + 0x13] + 1) & 0xff;
      if ((s[b + 0x13] & 0x03) === 0) {
        spawnChild(pool, s, b, 0x2a, 0);
        return;
      }
      spawnChild(pool, s, b, 0x2d, (Math.random() * 256) & 0x0c); // LD A,R
      return;
    }
  }
}

/**
 * The handler proper (0x8A5A).
 *
 * @returns {boolean} false when the shared entity update must be skipped
 */
export function runBaseSegment(pool, slot, ctx, type) {
  const s = pool.slots;
  const b = slot * ENTITY_STRIDE;
  const { rom, scroll, base, sound } = ctx;

  if ((s[b] & 0x80) === 0) {
    // ---- waiting to be let in (0x8A61) ---------------------------------
    if (scroll.flags & 0x02) s[b + 0x01] = (s[b + 0x01] + 8) & 0xff;
    if ((base.flags & 0x02) === 0) return false; // 0x8A75
    s[b] |= 0x80;
    // 0x8A7A: L keeps the Y from **before** the +0x10, and that pre-increment
    // Y is what 0x8948 turns into the tile address. Using the shifted Y puts
    // every segment two tile rows below the base art it belongs to.
    const tileY = s[b + 0x01] & 0xff;
    s[b + 0x01] = (s[b + 0x01] + 0x10) & 0xff; // 0x8A7E
    s[b + 0x05] = 0;
    s[b + 0x0c] = 0;
    s[b + 0x0d] = 1;
    // 0x8A8F: resolve the name-table address once and remember it, and file
    // it in the controller's per-segment table.
    const col = ((s[b + 0x02] - 0x20) & 0xff) >> 3;
    const row = (tileY >> 3) % 24;
    const addr = 0x3800 + row * 32 + col;
    s[b + 0x06] = addr & 0xff;
    s[b + 0x07] = addr >> 8;
    const idx = s[b + 0x1c];
    if (idx < base.listVram.length) base.listVram[idx] = addr;

    // 0x8AAD: the per-type parameter row.
    const e = BASE_SEGMENT_TABLE + (type - 73) * 5;
    s[b + 0x03] = rom.byte(e);
    s[b + 0x19] = rom.byte(e + 1);
    s[b + 0x01] = (s[b + 0x01] + rom.byte(e + 2)) & 0xff;
    s[b + 0x02] = (s[b + 0x02] + rom.byte(e + 3)) & 0xff;
    s[b + 0x15] = rom.byte(e + 4);
    s[b + 0x14] = 0;
    loadPatternRecord(s, b, rom, s[b + 0x0f] | (s[b + 0x10] << 8)); // 0x8AE5
  }

  // ---- dying (0x8AE8): tick the death counter, then leave a wreck --------
  if (s[b + 0x05] & 0x02) {
    s[b + 0x19] = (s[b + 0x19] - 1) & 0xff;
    if (s[b + 0x19] === 0) return segmentDies(ctx, pool, slot, s, b);
    if ((s[b + 0x19] & 0x03) === 0) drawWreck(ctx, s, b); // 0x8BBB
    return false;
  }

  // 0x8AEF tests the *entity type*, not the phase: the core (0xCF) has no
  // shutter animation and drops straight into the firing accumulator.
  let firing = type === 79;
  if (!firing) {
    // 0x8AF7: while enraged (0xE150 bit3), keep pace with the scroll.
    if (base.flags & 0x08 && scroll.flags & 0x02) {
      s[b + 0x01] = (s[b + 0x01] + 8) & 0xff;
    }
    // 0x8AFF: the shutter opens and closes, one phase per accumulator carry,
    // at a dwell rate the pattern record picks per phase.
    const phase = s[b + 0x0c];
    const rate = phase === 0 ? s[b + 0x09] : phase === 3 ? s[b + 0x0b] : s[b + 0x0a];
    const sum = s[b + 0x0e] + rate;
    if (sum <= 0xff) {
      s[b + 0x0e] = sum;
    } else {
      s[b + 0x0e] = 0;
      s[b + 0x0c] = (s[b + 0x0c] + s[b + 0x0d]) & 0xff;
      if (s[b + 0x0c] === 0) {
        // 0x8B4F: a full cycle - take the next pattern record, then reverse.
        loadPatternRecord(s, b, rom, s[b + 0x11] | (s[b + 0x12] << 8));
        s[b + 0x0d] = -s[b + 0x0d] & 0xff;
      } else if (s[b + 0x0c] === 3) {
        s[b + 0x0d] = -s[b + 0x0d] & 0xff; // 0x8B58: bounce off the top phase
      }
      drawSegment(ctx, s, b, type); // 0x8B60: all three paths repaint
    }
    // 0x8B63: fully shut means invisible and untouchable - not even collision.
    const phaseNow = s[b + 0x0c];
    if (phaseNow === 0) return false;
    firing = phaseNow === 3; // 0x8B68: only wide open does it shoot
  }

  // 0x8B6C: the firing accumulator.
  if (firing) {
    const sum = s[b + 0x14] + s[b + 0x15];
    s[b + 0x14] = sum & 0xff;
    if (sum > 0xff) fireSegment(ctx, s, b, type); // 0x8B77
  }

  // 0x8B7A entity_post, then 0x8B7D the shared box hit-sub. Everything above
  // that returns early, which is exactly why a segment cannot be shot before
  // the controller lets it into the fight.
  const hit = checkEntityCollisions(pool, rom, slot, ctx.player.fireMode, true);
  if (hit && hit.hitBy !== 0) {
    pool.clear(hit.hitBy);
    baseSegmentHit(ctx, pool, slot);
  } else if (hit) {
    collisionResponse(pool, rom, slot, 0); // the player flew into it
  }
  return false;
}

/** 0x8BAA / 0x8B9A: the two ways a segment leaves the fight. */
function segmentDies(ctx, pool, slot, s, b) {
  drawWreck(ctx, s, b); // 0x8CA2
  s[b] = 0x50; // becomes the standard explosion
  if (ctx.base.alive > 0) ctx.base.alive--; // 0x8BB1: (0xE152)--
  void pool;
  void slot;
  return false;
}

/**
 * The hit path, reached from the shared box hit-sub (0x7904) at 0x8B7D. The
 * core (shape 0x4F) does not explode on the spot: it flips into the dying
 * state and burns down through its own counter.
 */
export function baseSegmentHit(ctx, pool, slot) {
  const s = pool.slots;
  const b = slot * ENTITY_STRIDE;
  const hp = s[b + 0x19];
  if (hp === 0) return;
  s[b + 0x19] = hp - 1;
  if (s[b + 0x19] !== 0) {
    // 0x8B85: a surviving hit rumbles and repaints the damage state, but only
    // at the two HP thresholds the core's tile blocks switch on (0x8B90).
    ctx.sound.playEvent(0x11);
    if (s[b + 0x19] === 0x32 || s[b + 0x19] === 0x14) drawWreck(ctx, s, b);
    return;
  }
  if (s[b + 0x18] === 0x4f) {
    s[b] = 0xcf; // 0x8BA1: stay a segment, but start dying
    s[b + 0x05] |= 0x02;
    s[b + 0x19] = 0x20;
    return;
  }
  segmentDies(ctx, pool, slot, s, b);
}
