/**
 * Title screen: the attract sequence and the logo swirl.
 *
 * Ported from `title_intro_seq` (0x5A11), `draw_logo_row` (0x5BA0),
 * `lookup_swirl_coord` (0x5B91) and `draw_title_text` (0x5AC8).
 *
 * Routines that block on `wait_frames` in the original become generators here:
 * one `yield` is one frame, so the control flow keeps the shape of the asm.
 */

import { COLS, ROWS } from '../screen.js';
import { LOGO_BLOCKS } from '../assets.js';
import { drawScoreLabels, renderLivesScore } from './hud.js';
import { waitFrames } from './loop.js';
import { debugTitleTick } from './debug.js';

/**
 * `logo_tile_rows` (0x4827): six 18-tile strips on a 19-byte stride.
 *
 * The stride comes from the index math at 0x5BC3 (`4F 87 87 87 81 87 81`):
 * x -> 2x -> 4x -> 8x -> 9x -> 18x -> 19x. Nineteen decimal, not 0x19 - the KB
 * entry records "stride 25 (0x19)" and is wrong. With 19 the table ends exactly
 * at 0x4897, one byte before `entity_update` (0x4898); the logo tiles run in
 * unbroken order 0xB0..0xE6 across rows 0-4; and row 5 is eighteen 0x20s, the
 * blank strip the erase pass wants. Stride 25 breaks all three.
 */
const LOGO_TILE_ROWS = 0x4827;
const LOGO_ROW_STRIDE = 19;
const LOGO_ROW_TILES = 18;
/** Column from which `draw_logo_row` starts clipping at the right edge. */
const LOGO_CLIP_COL = 14;

/** `logo_swirl_path` (0x5B59): 28 entries of (col, row). */
const SWIRL_PATH = 0x5b59;
const SWIRL_STEPS = 0x1c;

/** The five logo rows enter staggered, from step 0x1C upward. */
const SWIRL_SEED = 0x1c;
const SWIRL_SEED_STEP = 4;
const LOGO_ROWS = 5;

/**
 * Strip index used by the erase pass (0x5A66 loads a literal 5): row 5 of the
 * table is the all-blank strip that wipes a row's previous position.
 */
const ERASE_STRIP = 5;

/** `lookup_swirl_coord` (0x5B91): entry byte 0 is the column, byte 1 the row. */
function lookupSwirlCoord(rom, step) {
  const addr = SWIRL_PATH + 2 * step;
  return { col: rom.byte(addr), row: rom.byte(addr + 1) };
}

/**
 * `draw_logo_row` (0x5BA0): blit one strip, skipping off-screen positions and
 * clipping the run at the right edge.
 */
function drawLogoRow(screen, rom, col, row, strip) {
  if (row >= ROWS || col >= COLS) return;
  const count = col < LOGO_CLIP_COL ? LOGO_ROW_TILES : COLS - col;
  const base = row * COLS + col;
  const src = LOGO_TILE_ROWS + LOGO_ROW_STRIDE * strip;
  for (let i = 0; i < count; i++) screen.nameTable[base + i] = rom.byte(src + i);
}

/** `draw_title_text` (0x5AC8): the credit lines, redrawn every swirl step. */
function drawTitleText(screen) {
  screen.writeNameTable(0x39e3, 'GAME DESIGNED BY COMPILE');
  screen.writeNameTable(0x3a03, 'PRODUCED      BY AII');
  screen.writeNameTable(0x3a23, 'PRESENTED     BY PONY INC.');
  screen.writeNameTable(0x3a43, 'COPYRIGHT @ 1986 PONY INC.');
  screen.writeNameTable(0x3a8e, [0xe7, 0xe9, 0xeb]);
  screen.writeNameTable(0x3aae, [0xe8, 0xea, 0xec]);
}

/**
 * `title_intro_seq` (0x5A11). Returns once a fire control is newly pressed.
 * @param {import('../context.js').Context} ctx
 */
export function* titleIntroSeq(ctx) {
  const { screen, rom, state, input, sound, assets } = ctx;

  input.firePressedEdge(); // 0x5A11: arm the edge detector
  sound.playEvent(3); // title music
  assets.loadTiles(screen, LOGO_BLOCKS);
  yield* waitFrames(2);
  screen.displayOn = true;

  drawScoreLabels(screen);
  renderLivesScore(screen, state);

  // 0x5A3D: seed the five row countdowns 0x1C, 0x20, 0x24, 0x28, 0x2C.
  const countdown = new Uint8Array(LOGO_ROWS);
  for (let r = 0; r < LOGO_ROWS; r++) countdown[r] = SWIRL_SEED + r * SWIRL_SEED_STEP;

  for (;;) {
    if (input.firePressedEdge()) return;

    // Erase pass (0x5A4E): blank the position each row currently occupies.
    for (let r = 0; r < LOGO_ROWS; r++) {
      const step = countdown[r];
      if (step === 0 || step >= SWIRL_STEPS) continue;
      const at = lookupSwirlCoord(rom, step);
      drawLogoRow(screen, rom, at.col, at.row + r, ERASE_STRIP);
    }

    drawTitleText(screen);

    // Advance pass (0x5A79): step each row along the path and redraw it.
    let home = 0;
    for (let r = 0; r < LOGO_ROWS; r++) {
      if (countdown[r] === 0) home++;
      else countdown[r]--;
      const step = countdown[r];
      if (step >= SWIRL_STEPS) continue;
      const at = lookupSwirlCoord(rom, step);
      drawLogoRow(screen, rom, at.col, at.row + r, r);
    }

    yield* waitFrames(2);
    if (home >= LOGO_ROWS) break;
  }

  // 0x5AB4: the subtitle, then idle until a fire control is pressed.
  screen.writeNameTable(0x396e, 'A.I.');
  for (;;) {
    // Port-only: D toggles debug mode, then 0-8 picks a round. Silent and
    // inert until D is pressed (web/src/game/debug.js).
    debugTitleTick(ctx);
    yield;
    if (input.firePressedEdge()) return;
  }
}
