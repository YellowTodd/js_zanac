/**
 * The base (boss) encounter — subsystem G's largest piece.
 *
 * A base is a cluster of destructible **segments** (entity types 73-79) placed
 * by a `place_tile_group` record whose descriptor has **bit 7** set. That bit
 * turns the placement batch into a base: every entity placed is appended to the
 * **attack list** at 0xE780 and counted into 0xE151, and when the batch ends
 * 0xE152 takes the count and 0xE150 becomes 1 — the encounter is armed.
 *
 * From there `base_tick` (0x8F5E, called from the main loop at 0x4077/0x40AC)
 * drives a four-phase state machine over 0xE150:
 *
 *   bit 0 only  approach - the scroll decelerates through
 *               `scroll_speed_ramp_table` as 0xE156 counts down, then stops
 *   bit 1       active   - segments animate and fire, the "TIME" countdown at
 *               (0xE154) runs, and 0xE152 tracks segments still alive
 *   bit 2       closing  - after a time-out the segments retreat; the encounter
 *               ends once they are all gone
 *   0           idle
 *
 * Clearing it (0xE152 reaching 0) runs the victory ceremony at 0x90A6, which
 * blocks on `gameplay_frame_loop` - hence the generator.
 *
 * Parameters come from map command 0xB (0x9742): four bytes into
 * 0xE155..0xE158, plus 0xE153 from `cmd11_index_table` (0x976C).
 */

import { ENTITY_STRIDE } from './state.js';
import { addScore, renderScoreBcd } from './hud.js';
import { mapScriptInit, mapScriptStep, placeTileGroup } from './scroll.js';
import { decEncounter } from './enemy.js';

/** `scroll_speed_ramp_table` (0x8F9A): approach deceleration caps. */
const SPEED_RAMP_TABLE = 0x8f9a;
/** `cmd11_index_table` (0x976C): 0xE157 scenario -> 0xE153 enrage threshold. */
export const CMD11_INDEX_TABLE = 0x976c;
/** `base_attack_patterns` (0x93AB): 8 pointers, then 3-byte records. */
const BASE_ATTACK_PATTERNS = 0x93ab;
/** `base_clear_award_index_table` (0x9302). */
const BASE_CLEAR_AWARD_TABLE = 0x9302;
/** `base_segment_table` (0x8DF1): 7 x 5 bytes for types 73-79. */
const BASE_SEGMENT_TABLE = 0x8df1;

/** Entity types 73-79 all run `handler_type73_base_segment` (0x8A5A). */
export const BASE_SEGMENT_TYPES = new Set([73, 74, 75, 76, 77, 78, 79]);

/** The attack list holds 8 records of 4 bytes at 0xE780. */
const ATTACK_LIST_MAX = 8;

/**
 * Everything the encounter keeps in the 0xE150 block, plus the attack list.
 * Named for the RAM addresses so the asm stays greppable.
 */
export class BaseState {
  constructor() {
    /** 0xE150 phase flags: bit0 armed, bit1 active, bit2 closing, bit3 enraged. */
    this.flags = 0;
    /** 0xE151 segments placed by the current batch (the list length). */
    this.placed = 0;
    /** 0xE152 segments still alive; reaching 0 clears the base. */
    this.alive = 0;
    /** 0xE153 enrage threshold from `cmd11_index_table`. */
    this.enrageAt = 0;
    /** 0xE154/0xE155 the on-screen countdown, BCD (low = "seconds"). */
    this.timeLo = 0;
    this.timeHi = 0;
    /** 0xE156 approach counter: 9..1 decelerate, 0 opens the base. */
    this.approach = 0;
    /** 0xE157 scenario byte: low 5 bits index the tables, high bits are flags. */
    this.scenario = 0;
    /** 0xE158 option bits (bit0 gates the ALC release, bit1 the E12D nudge). */
    this.options = 0;
    /** 0xE159 secondary BCD counter, seeded from 0xE155, -3 per minute. */
    this.aux = 0;
    /** 0xE15A 16-bit intro timer (0xC0 frames) before the alarm SFX. */
    this.introTimer = 0;
    /** 0xE717 round-robin cursor into the 8 attack-pattern pointers. */
    this.patternCursor = BASE_ATTACK_PATTERNS;
    /** 0xE780: 4-byte records {entity slot, VRAM address}. */
    this.list = new Int16Array(ATTACK_LIST_MAX).fill(-1);
    this.listVram = new Uint16Array(ATTACK_LIST_MAX);
    /** 0xE71E write cursor into that list. */
    this.listCursor = 0;
    /** Set for one frame when the clear ceremony should run. */
    this.cleared = false;
  }

  reset() {
    this.flags = 0;
    this.placed = 0;
    this.alive = 0;
    this.enrageAt = 0;
    this.timeLo = 0;
    this.timeHi = 0;
    this.approach = 0;
    this.scenario = 0;
    this.options = 0;
    this.aux = 0;
    this.introTimer = 0;
    this.patternCursor = BASE_ATTACK_PATTERNS;
    this.list.fill(-1);
    this.listVram.fill(0);
    this.listCursor = 0;
    this.cleared = false;
  }
}

/** BCD subtract of 1 (`SUB 1` + `DAA`), returning [value, borrow]. */
function bcdDec(v, by = 1) {
  let a = (v - by) & 0xff;
  let borrow = v - by < 0;
  // DAA after a subtraction fixes up each nibble that borrowed.
  if ((v & 0x0f) < (by & 0x0f)) a = (a - 0x06) & 0xff;
  if (borrow || (v & 0xf0) < (by & 0xf0)) a = (a - 0x60) & 0xff;
  return [a, borrow];
}

/**
 * `place_tile_group`'s base bookkeeping. Bit 7 of the descriptor (0x95F8)
 * restarts the list; each placed record appends to it (0x9626) and bumps
 * 0xE151; the batch end (0x9665) copies the count to 0xE152 and arms 0xE150.
 */
export function baseBatchBegin(base) {
  base.listCursor = 0;
  base.placed = 0;
  base.list.fill(-1);
}

/** @param {number} slot entity slot index just placed */
export function baseBatchAppend(base, slot) {
  if (base.listCursor < ATTACK_LIST_MAX) {
    base.list[base.listCursor] = slot;
    base.listCursor++;
  }
  base.placed = (base.placed + 1) & 0xff;
}

export function baseBatchEnd(base) {
  base.alive = base.placed;
  base.flags = 0x01;
}

/**
 * Map command 0xB (0x9742): load the four parameter bytes and derive 0xE153.
 * `(0xE154) = 0` starts the countdown at "0xE155 : 00".
 */
export function baseConfigure(base, rom, p) {
  base.timeHi = rom.byte(p); // 0xE155
  base.approach = rom.byte(p + 1); // 0xE156
  base.scenario = rom.byte(p + 2); // 0xE157
  base.options = rom.byte(p + 3); // 0xE158
  base.timeLo = 0; // 0x974A
  base.enrageAt = rom.byte(CMD11_INDEX_TABLE + (base.scenario & 0x1f));
}

/**
 * `base_tick` (0x8F5E) — one frame of the encounter state machine.
 *
 * @param {import('../context.js').Context} ctx
 * @returns {'idle'|'approach'|'active'|'closing'|'cleared'|'timeout'}
 */
export function baseTick(ctx) {
  const { base, scroll, rom, state } = ctx;
  const f = base.flags;

  if (f & 0x04) return baseClosing(ctx);
  if (f & 0x02) return baseActive(ctx);
  if ((f & 0x01) === 0) return 'idle';

  // ---- approach (0x8F72): tied to the scroll, not the frame rate ----------
  if ((scroll.flags & 0x02) === 0) return 'approach';
  base.approach = (base.approach - 1) & 0xff;
  const a = base.approach;
  if (a === 0) return baseOpen(ctx);
  if (a >= 0x0a) return 'approach';
  if ((base.scenario & 0x1f) >= 0x11) return 'approach';
  // 0x8F8E: the table is indexed from 0x8F99, i.e. entry (a - 1).
  const cap = rom.byte(SPEED_RAMP_TABLE + a - 1);
  if (cap < scroll.speed) scroll.speed = cap; // 0x8F98: only ever slower
  void state;
  return 'approach';
}

/** 0x8FA3: the scroll halts and the base opens for business. */
function baseOpen(ctx) {
  const { base, scroll, rom, sound, state } = ctx;
  scroll.speed = 0; // 0x8FA3 - this is the stall the player sees

  if (base.scenario & 0x20 && (state.flowFlags & 0x80) === 0) {
    sound.fadeMusic(); // 0x8FB1 -> 0x5211: ramp the theme down, don't cut it
  }
  base.introTimer = 0x00c0; // 0x8FB4

  const kind = (base.scenario & 0x1f) - 0x10;
  if (kind === 0) scroll.targetSpeed = 0; // 0x8FC3
  // kind == 1 (scenario 0x11) also splices in the 0xBCB2 tile group at 0x93E4;
  // that variant does not occur in the shipped scripts, so it is not wired.

  base.flags = 0x02; // 0x8FCA
  if ((base.options & 0x02) === 0) {
    if (ctx.spawn) ctx.spawn.ctrl |= 0x08; // 0x8FD4: SET 3,(E12D)
    base.aux = base.timeHi; // 0x8FDB
  }
  assignAttackPatterns(ctx);
  // 0x9014: unless scenario bit 4 disables the clock, print its label. The
  // "TIME" bytes are another 0x5C25 inline string (0x9020: 54 49 4D 45 00)
  // shown as instructions in the disassembly.
  if ((base.scenario & 0x10) === 0 && ctx.screen) {
    ctx.screen.writeNameTable(0x3ab9, 'TIME');
  }
  return 'active';
}

/**
 * 0x8FDE: hand each segment the next of the eight attack patterns, round
 * robin, and number it (+0x1C) so it can find its slot in the VRAM table.
 */
function assignAttackPatterns(ctx) {
  const { base, pool, rom } = ctx;
  base.patternCursor = BASE_ATTACK_PATTERNS;
  let remaining = 8; // C
  for (let i = 0; i < base.placed && i < ATTACK_LIST_MAX; i++) {
    const slot = base.list[i];
    let cursor = base.patternCursor;
    const ptr = rom.word(cursor);
    cursor += 2;
    if (--remaining === 0) {
      cursor = BASE_ATTACK_PATTERNS;
      remaining = 8;
    }
    base.patternCursor = cursor;
    if (slot < 0 || !pool.active(slot)) continue;
    const b = slot * ENTITY_STRIDE;
    pool.slots[b + 0x0f] = ptr & 0xff;
    pool.slots[b + 0x10] = ptr >> 8;
    pool.slots[b + 0x0e] = 0;
    pool.slots[b + 0x1c] = i;
  }
}

/** 0x9028: the fight itself. */
function baseActive(ctx) {
  const { base, sound, state } = ctx;

  // 0x9028: the intro timer, then the alarm.
  if (base.introTimer !== 0) {
    base.introTimer = (base.introTimer - 1) & 0xffff;
    if (
      base.introTimer === 0 &&
      base.scenario & 0x20 &&
      (state.flowFlags & 0x80) === 0
    ) {
      sound.playEvent(0x19); // 0x9044
    }
  }

  // 0x9047: the displayed countdown, unless bit 4 turns it off.
  if ((base.scenario & 0x10) === 0) {
    const [lo, borrow] = bcdDec(base.timeLo);
    if (!borrow) {
      base.timeLo = lo;
    } else {
      base.timeLo = 0x59; // 0x9057
      const [hi, hiBorrow] = bcdDec(base.timeHi);
      base.timeHi = hi;
      const [aux, auxBorrow] = bcdDec(base.aux, 3); // 0x9061
      base.aux = aux;
      if (auxBorrow && base.options & 0x01 && ctx.spawn) {
        ctx.spawn.ctrl &= ~0x08; // 0x906F: RES 3,(E12D)
      }
      if (hiBorrow) base.timeHi = 0;
    }
    // 0x907A: the units count, two BCD digits at 0x3ABD via render_hex_byte.
    if (ctx.screen) {
      ctx.screen.writeNameTable(0x3abd, [
        0x30 + ((base.timeHi >> 4) & 0x0f),
        0x30 + (base.timeHi & 0x0f),
      ]);
    }
    if (base.timeLo === 0 && base.timeHi === 0) return baseTimeout(ctx);
  }

  // 0x908A: segments left.
  if (base.alive === 0) {
    base.cleared = true;
    return 'cleared';
  }
  if (base.alive <= base.enrageAt) base.flags |= 0x08; // 0x9097
  return 'active';
}

/** 0x9325: the clock ran out - the base packs up instead of dying. */
function baseTimeout(ctx) {
  const { base, state } = ctx;
  if (ctx.spawn) {
    ctx.spawn.ctrl &= ~0x08; // 0x9325
    decEncounter(ctx); // 0x9329 dec_encounter_b -> 0xE130
    ctx.spawn.accHi = (ctx.spawn.accHi + 0x10) & 0xff; // 0x932F: E12E += 0x10
    if (ctx.spawn.accHi < 0xff) ctx.spawn.accHi++; // 0x9334 inc_encounter_a
    ctx.spawn.ctrl |= 0x01;
  }
  // 0x933D: the bit-5 scenario ducks the theme, 0x9345 wipes the clock.
  if (base.scenario & 0x20 && (state.flowFlags & 0x80) === 0) {
    ctx.sound.fadeMusic();
  }
  eraseTimeReadout(ctx);
  base.flags = 0x0e; // 0x9348
  return 'timeout';
}

/**
 * `SUB_9315`: six spaces over the TIME readout. The spaces are an inline
 * string after the 0x5C25 call (0x931B: `20 20 20 20 20 20 00`), which the
 * disassembly renders as a run of `JR NZ`s.
 */
function eraseTimeReadout(ctx) {
  if (ctx.screen) ctx.screen.writeNameTable(0x3ab9, '      ');
}

/**
 * 0x934D: wind-down. Sweep the attack list; `any` records that a segment slot
 * still holds a base type at all, `busy` counts those not yet in retreat
 * state 3. From 0x0E we wait for every segment to reach state 3, then drop to
 * 0x0C; from 0x0C we wait for them to vanish, then the encounter is over.
 */
function baseClosing(ctx) {
  const { base, pool } = ctx;
  let any = false;
  let busy = 0;
  for (let i = 0; i < base.placed && i < ATTACK_LIST_MAX; i++) {
    const slot = base.list[i];
    if (slot < 0) continue;
    const t = pool.slots[slot * ENTITY_STRIDE];
    if (t < 0xc9 || t >= 0xcf) continue; // 0x935B/0x935F: only live segments
    any = true;
    if (pool.slots[slot * ENTITY_STRIDE + 0x0c] === 3) continue;
    busy++;
  }

  if (base.flags & 0x02) {
    if (busy !== 0) return 'closing'; // 0x9378
    base.flags = 0x0c; // 0x937C
    if (base.scenario & 0x20) {
      // 0x9385: this scenario cut the music when the base opened, so the
      // retreat has to hand it back.
      ctx.sound.stopAll();
      restartRoundBgm(ctx);
    }
    return 'closing';
  }
  if (any) return 'closing'; // 0x938D
  base.flags = 0; // 0x938E
  return 'idle';
}

/**
 * The victory ceremony (0x90A6). Blocking in the ROM - it drives
 * `gameplay_frame_loop` directly - so it is a generator here: one `yield` per
 * frame, exactly like the ROM's frame waits.
 *
 * @param {import('../context.js').Context} ctx
 */
export function* baseClearCeremony(ctx) {
  const { base, pool, rom, screen, scroll, sound, state } = ctx;

  // 0x90A6: the ALC gets a big discount for clearing a base.
  if (ctx.spawn) {
    const acc = ctx.spawn.accHi;
    ctx.spawn.accHi = (acc - (acc >> 2)) & 0xff; // 0x90B1
    ctx.spawn.posBias = Math.max(0, ctx.spawn.posBias - 8); // 0x90BC
    if (ctx.spawn.accHi > 0) ctx.spawn.accHi--; // 0x90BF dec_encounter_a
    ctx.spawn.ctrl |= 0x01;
    // 0x90C2 SUB_bfc8 is a no-op here: 0xE150 bit 1 is still set, so the
    // encounter counter stays frozen until the flags are cleared below.
    ctx.spawn.ctrl &= ~0x08; // 0x90C5
  }
  base.flags = 0; // 0x90C9
  base.cleared = false;
  if (state.flowFlags & 0x80) return; // 0x90D2: already heading to the title

  // 0x90DC: leftover structure types 0x52/0x54-0x56 all become explosions.
  for (let slot = 5; slot < 26; slot++) {
    const b = slot * ENTITY_STRIDE;
    const t = pool.slots[b] & 0x7f;
    if (t === 0x53 || t < 0x52 || t >= 0x57) continue;
    pool.slots[b] = 0x50;
    pool.slots[b + 0x18] = 0;
  }

  // 0x90FE: two passes of "flash the backdrop white, blow everything up, and
  // rewrite the base's tiles into rubble".
  for (let pass = 2; pass >= 1; pass--) {
    if ((base.scenario & 0x80) === 0) {
      screen.backdrop = 0x0f; // 0x9108: WRTVDP(7, 0x0F)
      yield* frames(ctx, 3); // 0x910E
      rubbleSweep(scroll, pass);
      scroll.flags |= 0x01; // 0x914C: SET 0,(E700) - repaint from the ring
      screen.backdrop = 0x01;
    }
    explodeAll(ctx); // 0x914F
    yield* frames(ctx, 4); // 0x9154
  }

  // 0x915C: the fanfare, unless the scenario opts out.
  const kind = base.scenario & 0x1f;
  const fanfare = base.scenario & 0x20 ? 0x1a : 0x1b;
  if (kind !== 0x11) {
    sound.stopAll(); // 0x9170
    if (kind !== 0x10) {
      sound.playEvent(fanfare); // 0x917A
      yield* frames(ctx, 60); // 0x917D: wait out the tune
      sound.stopAll(); // 0x9180
    }
  }

  // 0x9183: scenario bit 6 suppresses the whole BONUS banner. The "BONUS"
  // text is a 0x5C25 inline string at 0x918F (42 4F 4E 55 53 00).
  const showBonus = (base.scenario & 0x40) === 0;
  if (showBonus) screen.writeNameTable(0x3966, 'BONUS');

  // 0x9198: high scenarios raise the round-clear flag.
  if (kind >= 0x10) state.flowFlags |= 0x04;

  // 0x91A6: the award, from the per-scenario index table. 0x91BD renders the
  // award entry's own BCD value at 0x396B before it is added to the score -
  // this is the "BONUS   2000" the player sees while the wreck burns.
  const award = rom.byte(BASE_CLEAR_AWARD_TABLE + kind);
  if (showBonus) {
    renderScoreBcd(screen, rom.slice(0x4aea + award * 3, 3), 0x396b);
  }
  addScore(state, rom, award, ctx); // 0x91C1

  if ((kind & 0x1e) !== 0x10) yield* frames(ctx, 0x64); // 0x91D0
  eraseTimeReadout(ctx); // 0x91D3 -> SUB_9315
  yield* frames(ctx, 0x28); // 0x91DB
  scroll.flags |= 0x01; // 0x91E1

  // 0x91EA: scenario 0x0F warps, above that is the ending; below, play on.
  if (state.flowFlags & 0x02) return;
  if (kind === 0x0f) {
    scroll.warpTarget = 0xb7a5; // 0x91F1: E722
    state.flowFlags |= 0x20; // 0x91FA
    return;
  }
  if (kind < 0x0f) {
    restartRoundBgm(ctx); // 0x91EC: JP C,0x4163
    return;
  }
  yield* endingSetup(ctx, kind - 0x0f); // 0x91EF
}

/**
 * `ending_setup` (0x91FD) — the three-beat finale after round 8's last base
 * (scenario 0xF0, kind 0x10) dies. Each beat ends by re-arming the base state
 * machine with the **next** scenario, so the cleared-base ceremony runs again
 * and dispatches the next beat: 0xF0 -> 0xD1 -> 0xB2 -> credits.
 *
 * Note the KB had `IX = 0xE700` here; the writes at 0x9231-0x9239 are
 * actually `0xE157/0xE156/0xE150` (IX = 0xE100) — scenario, approach count
 * and the armed flag. That is the whole chaining mechanism.
 */
function* endingSetup(ctx, phase) {
  if (phase === 1) {
    yield* endingRevealLogo(ctx); // LAB_91FD
  } else if (phase === 2) {
    yield* endingLetters(ctx); // 0x9254
  } else {
    yield* endingArmCredits(ctx); // LAB_92AF
  }
  ctx.state.flowFlags &= ~0x04; // clear_credits_busy (0x92CA): RES 2
}

/**
 * LAB_91FD: build the credits/logo tile screen from the mini-script at
 * 0xBBB4 — the ROM stashes the live 0xE800 ring in VRAM scratch, runs the
 * ordinary scroll engine over the credits stream, copies the result to
 * 0xEB00, restores the ring, and then reveals 0xEB00 column-pair by
 * column-pair (`copy_tile_column`) while the ending music (event 0x0C) plays.
 */
function* endingRevealLogo(ctx) {
  const { base, rom, scroll, screen, sound } = ctx;
  sound.stopAll(); // 0x9201

  // Snapshot everything the credits build will clobber (the VRAM-stash trick).
  const saved = {
    ring: Uint8Array.from(scroll.ring),
    groups: Uint8Array.from(scroll.groups),
    streams: Uint8Array.from(scroll.streams),
    ringRow: scroll.ringRow,
    levelRow: scroll.levelRow,
    nextCmdRow: scroll.nextCmdRow,
    streamPtr: scroll.streamPtr,
    halted: scroll.halted,
    speed: scroll.speed,
    speedAcc: scroll.speedAcc,
  };
  mapScriptInit(scroll, rom, 0xbbb4); // 0x920F -> init_credits_stream (0x941B)
  for (let i = 0; i < 24; i++) mapScriptStep(ctx); // 0x9216 build_tile_screen
  // 0xEB00: the finished screen, in screen-row order.
  const credits = new Uint8Array(24 * 24);
  for (let r = 0; r < 24; r++) {
    const src = ((scroll.ringRow + r) % 24) * 24;
    credits.set(scroll.ring.subarray(src, src + 24), r * 24);
  }
  scroll.ring.set(saved.ring);
  scroll.groups.set(saved.groups);
  scroll.streams.set(saved.streams);
  scroll.ringRow = saved.ringRow;
  scroll.levelRow = saved.levelRow;
  scroll.nextCmdRow = saved.nextCmdRow;
  scroll.streamPtr = saved.streamPtr;
  scroll.halted = saved.halted;
  scroll.speed = saved.speed;
  scroll.speedAcc = saved.speedAcc;

  sound.playEvent(0x0c); // 0x9245: the ending theme

  // The E700=0x0C reveal phase: one symmetric column pair per row event
  // (E710 = 0x20 -> one event every eight frames).
  for (let pair = 0; pair < 12; pair++) {
    for (const col of [pair, 23 - pair]) {
      for (let r = 0; r < 24; r++) {
        const tile = credits[r * 24 + col];
        scroll.ring[((scroll.ringRow + r) % 24) * 24 + col] = tile;
        screen.nameTable[r * 32 + col] = tile;
      }
    }
    yield* frames(ctx, 8);
  }

  // 0x9231: chain to the next beat - scenario 0xD1, approach 12, re-armed.
  base.scenario = 0xd1;
  base.approach = 0x0c;
  base.flags = 0x01;
  base.placed = 0;
  base.alive = 0;
  ctx.scroll.speed = 0x20; // 0x9240: E710 = 0x20 so the approach can count
}

/**
 * 0x9254: the "letters" beat — nine 17-tile rows from 0xBBFD stamped upward
 * from VRAM 0x3924, each arriving with a seven-explosion burst at its height
 * (`SUB_92F3` -> 0x8BCA), then the tile group at 0xBBF3 is spliced into
 * stream slot 0 and the machine chains to scenario 0xB2.
 */
function* endingLetters(ctx) {
  const { base, pool, rom, scroll, screen } = ctx;
  yield* frames(ctx, 2); // 0x9254

  let addr = 0x3924;
  let src = 0xbbfd;
  let y = 0x4c;
  for (let r = 0; r < 9; r++) {
    // SUB_92F3: seven debris explosions scattered around (y, x=0x80).
    for (let i = 0; i < 7; i++) {
      const q = pool.allocEntitySlot();
      if (q < 0) break;
      pool.clear(q);
      const e = q * 32;
      const rnd = prngWord();
      pool.slots[e] = 0x23;
      pool.slots[e + 0x01] = (y + (rnd & 0x1f) - 0x10) & 0xff;
      pool.slots[e + 0x02] = (0x80 + ((rnd >> 8) & 0x1f) - 0x10) & 0xff;
      pool.slots[e + 0x18] = 0;
    }
    const row = (addr - 0x3800) >> 5;
    const col = addr & 0x1f;
    for (let i = 0; i < 0x11; i++) {
      const tile = rom.byte(src + i);
      screen.nameTable[row * 32 + col + i] = tile;
      scroll.ring[((scroll.ringRow + row) % 24) * 24 + col + i] = tile;
    }
    yield* frames(ctx, 6); // 0x9285
    addr -= 0x20;
    src += 0x11;
    y -= 8;
  }

  placeTileGroup(scroll, rom, 0xbbf3, 8); // 0x929D: SUB_93E7, column base 8
  base.scenario = 0xb2; // 0x92A0 chains to the credits beat
  base.approach = 0x01;
  base.flags = 0x01;
  base.placed = 0;
  base.alive = 0;
  ctx.scroll.speed = 0x20;
  yield* frames(ctx, 10); // 0x92A4
}

/** A tiny local PRNG word for the debris scatter (the ROM uses R). */
let endingRngState = 0x1234;
function prngWord() {
  endingRngState ^= (endingRngState << 7) & 0xffff;
  endingRngState ^= endingRngState >> 9;
  endingRngState ^= (endingRngState << 8) & 0xffff;
  return endingRngState;
}

/**
 * LAB_92AF: arm the staff credits. The ending stream 0xA6F4 goes into 0xE722,
 * bit 5 hands control to `level_complete_handler` (round 8 -> round 0, both
 * multiples of 8, so the **logo tiles load** on path C) and bit 3 turns the
 * per-frame credits display on. The scroll then runs fast (0xE712 = 0x80)
 * under the roll, with the ship still flyable.
 */
function* endingArmCredits(ctx) {
  const { scroll, state } = ctx;
  scroll.warpTarget = 0xa6f4; // 0x92AF: E722
  state.flowFlags |= 0x20 | 0x08; // 0x92B8/0x92BA: bits 5 and 3
  yield* frames(ctx, 0x3c); // 0x92BC
  scroll.targetSpeed = 0x80; // 0x92C7: E712
}

/**
 * `restart_round_bgm` (0x4163). The fanfare path leaves the PSG silent, so
 * every route out of a base encounter has to put the theme back: event 1, or
 * event 2 on rounds that are a multiple of 8. If 0xE102 bit 7 is already set
 * the game is on its way to the title, so it stays quiet.
 *
 * Missing this is why the music never came back after a boss fight.
 */
export function restartRoundBgm(ctx) {
  if (ctx.state.flowFlags & 0x80) return; // 0x4166: heading to the title
  ctx.sound.playEvent((ctx.state.round & 0x07) !== 0 ? 1 : 2);
}

/** Run `n` frames of the normal loop (0x9393 `gameplay_frame_loop`). */
function* frames(ctx, n) {
  for (let i = 0; i < n; i++) yield;
}

/**
 * 0x9118/0x9131: rewrite the base's tile codes in the scroll ring into rubble.
 * Pass 2 folds 0xA0.. into 0xE7 (with 0xA7-0xAA lifted to 0xE3-0xE6); pass 1
 * then folds 0xE3-0xE7 down into the 0x3A-0x3E crater tiles.
 */
function rubbleSweep(scroll, pass) {
  const ring = scroll.ring;
  for (let i = 0; i < ring.length; i++) {
    const v = ring[i];
    if (pass === 2) {
      if (v < 0xa0) continue;
      ring[i] = 0xe7;
      if (v < 0xa7 || v >= 0xab) continue;
      ring[i] = (v + 0x3c) & 0xff;
    } else {
      if (v < 0xe3 || v >= 0xe8) continue;
      ring[i] = 0x3e;
      if (v === 0xe7) continue;
      ring[i] = (v - 0xa9) & 0xff;
    }
  }
}

/** `explode_enemies` (0x8A26) as the ceremony calls it. */
function explodeAll(ctx) {
  const { pool } = ctx;
  for (let slot = 4; slot < 26; slot++) {
    if (!pool.active(slot)) continue;
    const b = slot * ENTITY_STRIDE;
    const t = pool.slots[b] & 0x7f;
    if (t === 0x23 || t === 0x50) continue;
    pool.slots[b + 0x18] = t;
    pool.slots[b] = 0x23;
  }
}

export { BASE_SEGMENT_TABLE, BASE_ATTACK_PATTERNS };
