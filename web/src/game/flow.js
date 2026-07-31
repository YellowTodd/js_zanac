/**
 * Top-level game flow: `cold_start` (0x4010) and `main_game_loop` (0x4042).
 */

import { CHARSET_BLOCKS, BG_LATE_BLOCKS, LOGO_BLOCKS } from '../assets.js';
import { KEY_ESC } from '../input.js';
import { titleIntroSeq } from './title.js';
import { waitFrames, pauseHandler } from './loop.js';
import {
  drawHudPanel,
  updateStatusBar,
  drawAlcReadout,
  compareSaveHiscore,
  scoreDisplayUpdate,
} from './hud.js';
import {
  ScrollState,
  mapScriptInit,
  mapScriptStep,
  scrollVelocityTick,
  scrollVramWrite,
  PLAYFIELD_ROWS,
} from './scroll.js';
import { SpawnState, spawnTick } from './spawn.js';
import {
  checkEntityCollisions,
  collisionResponse,
  STRUCT_SLOT_FIRST,
  STRUCT_SLOT_LAST,
} from './collision.js';
import {
  PlayerState,
  loadShotParams,
  spawnPlayerShip,
  playerShipUpdate,
  updateEntities,
  fireSelect,
  updateFireDisplay,
  resetShipPower,
} from './player.js';
import { runPlayerDeath, PICKUP_TYPES, WIDE_STRUCTURE_TYPES } from './enemy.js';
import {
  BaseState,
  BASE_SEGMENT_TYPES,
  baseTick,
  baseClearCeremony,
  restartRoundBgm,
} from './base.js';
import { EntityPool, entityUpdate, SLOT_PLAYER } from './entity.js';

/** `stage_stream_ptr_table` (0x945C): one map-script pointer per round. */
const STAGE_STREAM_PTR_TABLE = 0x945c;

/**
 * `init_screen_mode` (0x428A): reprogram the VDP, reload the charset and
 * sprites, blank the name table to spaces, park the sprites, clear entities.
 * @param {import('../context.js').Context} ctx
 */
export function initScreenMode(ctx) {
  ctx.assets.loadTiles(ctx.screen, CHARSET_BLOCKS);
  ctx.screen.fillNameTable(0x20);
  ctx.screen.hideSprites();
  ctx.screen.displayOn = false; // init_vdp_regs writes R1 with BL = 0
}

/**
 * `title_screen_init` (0x41DB): reset the per-session state, honour the
 * ESC-continue secret, then select the round's map script.
 *
 * ESC held while starting leaves 0xE701 alone, so play resumes at the last
 * round reached this power cycle (kb/guides/keyboard-input.md).
 * @param {import('../context.js').Context} ctx
 */
export function* titleScreenInit(ctx) {
  const { screen, state, sound, input, rom, assets } = ctx;

  screen.displayOn = false;
  sound.stopAll();

  state.score.fill(0);
  state.flowFlags = 0;
  state.inGame = 0;

  const escHeld = input.isDown(KEY_ESC); // check_esc_key (0x43D2)
  initScreenMode(ctx);
  // The debug round select (port-only) rides the same rail as the ESC
  // continue: both simply mean "do not force round 1".
  if (!escHeld && !ctx.debugRoundArmed) state.round = 1;
  ctx.debugRoundArmed = false; // one shot - the next title screen re-arms

  // 0x425A: the map-script table is indexed by (8 - round); rounds 0 and 8
  // additionally swap in the late-stage terrain tiles.
  const index = (8 - state.round) & 0xff;
  if ((index & 7) === 0) assets.loadTiles(screen, BG_LATE_BLOCKS);
  state.streamPtr = rom.word(STAGE_STREAM_PTR_TABLE + 2 * index);

  yield; // the routine spans a frame boundary before gameplay starts
}

/** `main_game_loop` (0x4042): title, then one play session. */
export function* mainGameLoop(ctx) {
  ctx.sound.stopAll();
  initScreenMode(ctx);
  ctx.state.inGame = 0;

  yield* titleIntroSeq(ctx);
  yield* titleScreenInit(ctx);
  yield* waitFrames(2);
  ctx.screen.displayOn = true;

  // 0x405A: rounds that are a multiple of 8 open with event 2, others with 7.
  ctx.sound.playEvent((ctx.state.round & 7) !== 0 ? 7 : 2);

  yield* gameplayLoop(ctx);
}

/**
 * Gameplay loop (0x4074 onward). Currently the background only: the scroll
 * engine advances the map script and streams tile rows into the name table.
 * The player, entities and HUD land in later slices.
 * @param {import('../context.js').Context} ctx
 */
function* gameplayLoop(ctx) {
  const { screen, state, rom } = ctx;
  const scroll = ctx.scroll ?? (ctx.scroll = new ScrollState());
  const pool = ctx.pool ?? (ctx.pool = new EntityPool());
  ctx.player ?? (ctx.player = new PlayerState());

  const spawn = ctx.spawn ?? (ctx.spawn = new SpawnState());
  const base = ctx.base ?? (ctx.base = new BaseState());
  scroll.reset();
  pool.reset();
  spawn.reset();
  base.reset();
  scroll.base = base; // place_tile_group arms the encounter through this
  // title_screen_init: 0x4225 seeds 0xE12D = 3 (stream active + recompute
  // requested) and 0x41F9 seeds 0xE124 = 6, the first immediate-spawn
  // countdown. Seeded here because ctx.spawn does not exist yet when
  // titleScreenInit runs on the first session.
  spawn.ctrl = 0x03;
  spawn.killCounter = 6;
  state.lives = 3; // 0x41E5: LD (IX+0x0A),3
  // Map-script cmd C (0x977D): scripted ALC nudge into the accumulators.
  // 0x977D: positive operands raise only 0xE132 (saturating at 0xFF); the
  // 0xE12E accumulator is touched on the negative path alone (clamped at 0).
  ctx.onSpawnPace = (delta) => {
    if (delta >= 0) {
      spawn.posBias = Math.min(0xff, spawn.posBias + delta);
    } else {
      spawn.posBias = Math.max(0, spawn.posBias + delta);
      spawn.accHi = Math.max(0, spawn.accHi + delta);
    }
    spawn.ctrl |= 0x01;
  };
  scroll.pool = pool; // greeble streams spawn ground structures into it
  loadShotParams(ctx.player, rom);
  fireSelect(ctx.player, rom, 0, ctx); // fire_reset -> fire_select(0) at round start
  scroll.stage = (8 - state.round) & 0xff;
  scroll.targetSpeed = 0x34; // title_screen_init seeds 0xE712 = 0x34
  mapScriptInit(scroll, rom, state.streamPtr);

  // Map cmd 8 (0x9699): print " ROUND n" once at VRAM 0x3948 and start the
  // 0x96-frame countdown at 0xE15E. display_timer_countdown (0x41BA) just
  // decrements it - gameplay keeps running - and on expiry clear_title_state
  // wipes the sprite shadow. The banner is printed once; the scroll blits
  // over it naturally as the round picks up speed (it starts from 0).
  ctx.onRoundBanner = () => {
    state.bannerTimer = 0x96;
    screen.writeNameTable(0x3948, ' ROUND ' + String(state.round & 0x0f) + ' ');
    scroll.protectRow = 10; // 0xE180[10]: shield the banner from the blit
    scroll.protectStart = 8;
    scroll.protectWidth = 9;
  };

  // Map command 9 (0x96DE -> 0x9433): an **in-place** script jump. It
  // resolves and stores the new round number and repaints the round digit,
  // then enters map_script_init at 0x941B - deliberately past the slot wipe -
  // so the terrain streams carry straight on. This is how rounds 1-7 chain;
  // it is not the level-complete ceremony.
  ctx.onRoundJump = (target) => {
    state.round = resolveRoundFromPtr(rom, target);
    mapScriptInit(scroll, rom, target);
  };

  screen.fillNameTable(0x20);
  drawHudPanel(screen); // draw_hud_labels (0x4BD4), once per round entry

  // `build_tile_screen` (0x946E): run the row step 24 times so the playfield
  // starts full instead of scrolling in from an empty screen.
  for (let i = 0; i < PLAYFIELD_ROWS; i++) mapScriptStep(ctx);
  scrollVramWrite(screen, scroll);

  for (;;) {
    if (scrollVelocityTick(scroll)) mapScriptStep(ctx);
    scrollVramWrite(screen, scroll);

    // `base_tick` (0x8F5E) runs from the main loop at 0x4077, before the
    // entity pass, so a base that opens this frame lets its segments in
    // immediately.
    // 0x9399: the pause sits inside `gameplay_frame_loop`, so everything
    // below it - entities, spawning, collisions - simply stops.
    yield* pauseHandler(ctx);

    baseTick(ctx);
    if (ctx.base.cleared) yield* baseClearCeremony(ctx);

    // 0x408A: the level-complete flag is tested every frame, before the
    // entity pass.
    if (state.flowFlags & 0x20) yield* levelCompleteSeq(ctx);

    // `gameplay_frame_loop` order: the ship handler runs first (slot 0), then
    // the rest of the pool, then the sprite shadow is flushed.
    spawnTick(ctx); // ground_struct_spawn_ctrl, main loop 0x4082
    pool.beginFrame();
    if (pool.type(SLOT_PLAYER) === 60) {
      // collision_response remapped the ship; run the death sequence.
      const phase = runPlayerDeath(ctx);
      if (phase === 'revert') playerShipUpdate(ctx);
      else if (phase === 'animating') entityUpdate(pool, SLOT_PLAYER, rom);
      else {
        // player_hit_handler (0x4649): one life gone.
        state.lives--;
        if (state.lives <= 0) {
          yield* gameOverSeq(ctx); // 0x4663
          return; // the main loop sees 0xE102 bit 7 and goes to the title
        }
      }
    } else {
      if (pool.slots[SLOT_PLAYER * 32] === 0) {
        // 0x75D5 only reaches its tail when the slot was empty, i.e. on a
        // fresh spawn; that tail wipes the shot level (0x7602).
        spawnPlayerShip(pool);
        resetShipPower(ctx);
      }
      playerShipUpdate(ctx);
    }
    updateEntities(ctx);
    resolveCollisions(ctx);
    scoreDisplayUpdate(screen, state); // 0x939C, the new-record flash
    updateStatusBar(screen, state, ctx.player);
    updateFireDisplay(screen, ctx.player);
    drawAlcReadout(screen, spawn); // base_encounter_ctrl (0xBFD6)
    if (state.flowFlags & 0x08) creditsTick(ctx); // 0x46D5, E102 bit 3
    if (state.bannerTimer > 0 && --state.bannerTimer === 0) {
      scroll.protectRow = -1; // clear_title_state: unshield; next blit reclaims
    }
    pool.flushSprites(screen);

    yield;
    if (ctx.input.isDown('Escape')) return;
  }
}

/** `credits_control_table` (0x4775) and its strings (0x47AA). */
const CREDITS_CONTROL = 0x4775;
const CREDITS_STRINGS = 0x47aa;

/**
 * `credits_display` (0x46D9) as a per-frame overlay. In the ROM it is a
 * blocking loop that drives `gameplay_frame_loop` itself — the round-0
 * terrain keeps scrolling and the ship stays flyable underneath — so here it
 * runs as a tick inside the ordinary loop instead.
 *
 * Page format, from the control table: one byte per text row starting at row
 * 5 — a string index into the length-prefixed list at 0x47AA (0 = blank
 * row). Each printed string is centred (`col = 12 - ((len + 2) >> 1)`),
 * wrapped in spaces, and gets its own 0xE180 protect window so the scroll
 * blit leaves it alone. The final page's "strings" 0x12-0x16 are the ZANAC
 * **logo tile rows** — the logo is literally typeset by the credits printer.
 * A 0xFF ends the page (delay 0x190); a double 0xFF ends the roll (delay
 * 0x4B0) and loops it. A fire press restarts the current delay; ESC leaves
 * for the title through the loop's normal exit.
 *
 * @param {import('../context.js').Context} ctx
 */
function creditsTick(ctx) {
  const { rom, screen, scroll, state, input } = ctx;
  const cr =
    ctx.creditsState ??
    (ctx.creditsState = { idx: 0, phase: 'print', timer: 0, fireWas: true });

  const fireDown =
    input.isDown('Space') || input.isDown('ShiftLeft') || input.isDown('KeyZ');
  const fireEdge = fireDown && !cr.fireWas;
  cr.fireWas = fireDown;

  if (cr.phase === 'print') {
    compareSaveHiscore(state); // 0x46DD, once per pass
    let row = 5; // 0x46F1: E15D
    let p = CREDITS_CONTROL + cr.idx;
    for (;;) {
      const strIdx = rom.byte(p);
      if (strIdx === 0xff) {
        cr.idx = p - CREDITS_CONTROL + 1;
        // 0x474E: a second 0xFF means the roll is over - loop it, slowly.
        if (rom.byte(p + 1) === 0xff) {
          cr.idx = 0;
          cr.timer = 0x4b0;
        } else {
          cr.timer = 0x190;
        }
        break;
      }
      if (strIdx !== 0) {
        // 0x46FE: skip strIdx length-prefixed strings, then print.
        let sp = CREDITS_STRINGS;
        for (let n = 0; n < strIdx; n++) sp += rom.byte(sp) + 1;
        const len = rom.byte(sp);
        if (len !== 0) {
          const col = 12 - ((len + 2) >> 1); // 0x4709
          const tiles = new Uint8Array(len + 2);
          tiles[0] = 0x20;
          for (let i = 0; i < len; i++) tiles[1 + i] = rom.byte(sp + 1 + i);
          tiles[len + 1] = 0x20;
          screen.writeNameTable(0x3800 + row * 32 + col, tiles);
          scroll.protectMap[row * 2] = col; // 0x4711: IY+0 / IY+0x18
          scroll.protectMap[row * 2 + 1] = len + 2;
        }
      }
      p++;
      row++;
      if (row >= 24) break; // safety; the ROM tables never overrun
    }
    cr.phase = 'wait';
    return;
  }

  if (cr.phase === 'wait') {
    if (fireEdge) cr.timer = cr.idx === 0 ? 0x4b0 : 0x190; // 0x475F re-arms
    if (--cr.timer > 0) return;
    scroll.protectMap.fill(0); // 0x4761 clear_title_state - the blit reclaims
    cr.phase = 'settle';
    cr.timer = 0x50; // 0x4764
    return;
  }

  // 'settle' (0x4767): ESC exits through the loop's own check; otherwise the
  // next page prints when the timer runs out.
  if (fireEdge) cr.timer = 0x50;
  if (--cr.timer <= 0) cr.phase = 'print';
}

/**
 * `game_over_handler` (0x4663). The lives ran out: save the high score, play
 * the game-over jingle (event 4), and hold " GAME OVER " over the frozen
 * playfield for up to 800 frames — a fresh press of a fire key skips the
 * wait (0x46BC arms an edge detector, so a key still held from the fatal
 * moment does not).
 *
 * The banner goes through the same 0xE180 per-row shield as the ROUND text:
 * 0x4677 writes count 7 / resume 0x12 for row 12, i.e. columns 7-17 — exactly
 * the 11 characters of " GAME OVER " at VRAM 0x3987. The string itself is a
 * 0x5C25 inline literal at 0x4692.
 *
 * @param {import('../context.js').Context} ctx
 */
function* gameOverSeq(ctx) {
  const { pool, screen, scroll, sound, state, input } = ctx;

  state.flowFlags |= 0x80; // 0x466A: SET 7 - go_to_title, before anything else
  for (let slot = 5; slot < 26; slot++) pool.clear(slot); // 0x40BA + dispatch
  if (ctx.base) ctx.base.flags = 0;
  if (ctx.spawn) ctx.spawn.posBias = 0;
  pool.beginFrame();
  pool.flushSprites(screen); // the SAT empties along with the pool

  compareSaveHiscore(state); // 0x4ACE
  sound.stopAll();
  sound.playEvent(0x04); // the game-over jingle

  scroll.protectRow = 12; // 0x4677: shield row 12, columns 7-17
  scroll.protectStart = 7;
  scroll.protectWidth = 11;
  screen.writeNameTable(0x3987, ' GAME OVER ');

  let prevDown = true; // 0x46BC: armed only after a release
  for (let f = 0; f < 800; f++) {
    const down =
      input.isDown('Space') || input.isDown('ShiftLeft') || input.isDown('KeyZ');
    if (!prevDown && down) break;
    prevDown = down;
    yield;
  }
  scroll.protectRow = -1;
}

/**
 * `level_complete_handler` (0x40DA) — the round transition, reached whenever
 * 0xE102 bit 5 is set (a black warp orb, a scenario-0x0F base, or the ending
 * hop).
 *
 * The ROM blocks here for about 1.7 seconds, so this is a generator. The order
 * matters and is easy to get wrong:
 *
 * 1. `reset_entities` (0x40BA) runs **before** the 0xE722 test, retypes slots
 *    **5-25 only** to 0x28 (whose handler is a plain `entity_clear`), and
 *    zeroes 0xE150 and 0xE132. Slots 0-4 - the ship, its three shots and the
 *    fire weapon - are deliberately spared.
 * 2. With no destination the routine falls straight to 0x414D.
 * 3. Otherwise: transition SFX, resolve the round, one entity pass so the
 *    0x28 retypes actually take effect, blank the ring, dissolve out, **hold
 *    the blank screen for 100 frames**, then rebuild and dissolve in.
 * 4. 0x414D always clears bit 5 and adds 0x20 to 0xE132.
 *
 * @param {import('../context.js').Context} ctx
 */
function* levelCompleteSeq(ctx) {
  const { pool, rom, screen, scroll, state, sound, assets } = ctx;

  // 0x40BA reset_entities - note the slot range and that it runs first.
  for (let slot = 5; slot < 26; slot++) {
    if ((pool.slots[slot * 32] & 0x7f) !== 0) pool.slots[slot * 32] = 0x28;
  }
  if (ctx.base) ctx.base.flags = 0; // 0xE150 = 0
  if (ctx.spawn) ctx.spawn.posBias = 0; // 0xE132 = 0

  const target = scroll.warpTarget;
  if (target !== 0) {
    sound.stopAll(); // 0x40E5
    sound.playEvent(0x0b); // 0x40EA: transition SFX
    const newRound = resolveRoundFromPtr(rom, target); // 0x40ED
    // 0x40F2: one entity_dispatch pass is what actually executes the 0x28
    // despawns - without it the slots keep their old types.
    for (let slot = 5; slot < 26; slot++) {
      if ((pool.slots[slot * 32] & 0x7f) === 0x28) pool.clear(slot);
    }
    scroll.ring.fill(0); // 0x40F8: 0xE800..0xEA3F = 0
    dissolveBlit(ctx); // 0x4105: 576 scattered cells - here, all zeros
    yield* waitFrames(100); // 0x410A
    scroll.protectRow = -1; // 0x4110 clear_title_state

    const oldRound = state.round; // 0x4117
    state.round = newRound; // 0x4118
    if ((newRound & 7) !== 0) {
      restartRoundBgm(ctx); // path A: rounds 1-7 reuse the resident tiles
    } else if ((oldRound & 7) !== 0) {
      assets.loadTiles(screen, BG_LATE_BLOCKS); // path B (0x4122)
      sound.stopAll();
      restartRoundBgm(ctx);
    } else {
      sound.stopAll(); // path C (0x412A): the 8 -> 0 ending hop
      assets.loadTiles(screen, CHARSET_BLOCKS);
      assets.loadTiles(screen, LOGO_BLOCKS);
      sound.playEvent(0x0a);
    }

    mapScriptInit(scroll, rom, target, true); // 0x413E: with the slot wipe
    scroll.ringRow = 0; // 0x4141 scroll_sync resets 0xE714
    for (let i = 0; i < PLAYFIELD_ROWS; i++) mapScriptStep(ctx); // 0x4144
    dissolveBlit(ctx); // 0x4147
    scroll.warpTarget = 0;
  }

  // 0x414D
  state.flowFlags &= ~0x20;
  if (ctx.spawn) ctx.spawn.posBias = Math.min(0xff, ctx.spawn.posBias + 0x20);
}

/**
 * `sub_4177` (0x4177): the round-transition wipe. 576 single-cell VDP writes
 * walking `x -= 1` and `y -= 5` (with an extra `y -= 1` on each x wrap), so
 * the playfield dissolves rather than sweeping. Every cell is written exactly
 * once and the whole thing finishes inside a frame or two, so the *result* is
 * a plain ring-to-name-table copy of columns 0-23; the scatter is only what
 * it looks like mid-blit. Columns 24-31 (the status panel) are never touched.
 */
function dissolveBlit(ctx) {
  const { screen, scroll } = ctx;
  for (let row = 0; row < PLAYFIELD_ROWS; row++) {
    const src = ((scroll.ringRow + row) % PLAYFIELD_ROWS) * 24;
    for (let col = 0; col < 24; col++) {
      screen.nameTable[row * 32 + col] = scroll.ring[src + col];
    }
  }
}

/**
 * `entity_post` (0x44BA) across the pool: every structure/enemy slot is tested
 * against the player's shots and the player.
 *
 * The response is `collision_response` (0x453E), which remaps both types
 * through `death_transition_table` (0x716B).
 * @param {import('../context.js').Context} ctx
 */
function resolveCollisions(ctx) {
  const { pool, rom, state } = ctx;
  for (let slot = STRUCT_SLOT_FIRST; slot <= STRUCT_SLOT_LAST; slot++) {
    if (!pool.active(slot)) continue;
    // Pickups collide through the player-only path (0x44B0) inside their
    // own handlers; shots pass straight through them.
    if (PICKUP_TYPES.has(pool.type(slot))) continue;
    const t = pool.type(slot);
    if ((t >= 4 && t <= 6) || t === 68) continue; // boxes soak hits themselves
    // Collision belongs to handlers that call entity_post; the death/explosion
    // handlers (35/60/80, and the fire-expire transient 19) never do, so a
    // burning wreck cannot chain-hit the shield or neighbours (0x84C9/0x8E2D
    // run entity_update or entity_clear only).
    if (t === 19 || t === 35 || t === 60 || t === 80) continue;
    if (WIDE_STRUCTURE_TYPES.has(t)) continue; // 0x87CA hit points, handled in runTypeHandler
    if (t === 72) continue; // the orb collides via 0x44B0 (player only)
    if (t === 61) continue; // the walker's kill lottery lives in its handler
    // Base segments post themselves at 0x8B7A, inside the handler, so that
    // the many early returns above it really do skip collision.
    if (BASE_SEGMENT_TYPES.has(t)) continue;
    const hit = checkEntityCollisions(pool, rom, slot, ctx.player.fireMode);
    if (!hit) continue;
    collisionResponse(pool, rom, slot, hit.hitBy);
    if (hit.hitBy !== 0) state.hits++;
    else state.playerHits++;
  }
}

/**
 * `resolve_round_from_ptr` (0x9444): the pointer table descends, so walking it
 * from the top and stopping at the first entry the pointer is >= yields the
 * round number directly. Using >= rather than equality means a pointer landing
 * part-way into a script (as warp destinations do) still resolves.
 */
function resolveRoundFromPtr(rom, ptr) {
  for (let index = 0, round = 8; index < 8; index++, round--) {
    if (ptr >= rom.word(STAGE_STREAM_PTR_TABLE + 2 * index)) return round;
  }
  return 0;
}

/** `cold_start` (0x4010). */
export function* coldStart(ctx) {
  ctx.state.reset();
  for (;;) yield* mainGameLoop(ctx);
}
