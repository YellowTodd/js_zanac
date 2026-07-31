/**
 * Development affordances that are **not in the ROM**.
 *
 * Everything here is additive and lives outside the ported routines, so the
 * byte-faithful code never has to know it exists.
 *
 * Debug mode is **off** until you press the **backquote key (`) on the title
 * screen**, which toggles it; the title looks completely stock until you do.
 * Backquote is used because every letter that reads like "debug" is already a
 * game control - D is WASD's right, X and Z are fire, S is down - and it is
 * the conventional console key besides. Once debug is on, **0-8** picks the
 * starting round; the choice rides the same rail as the ESC-continue secret,
 * because `title_screen_init` only forces round 1 when nothing else has armed
 * it.
 *
 * The mode itself persists across title screens (and across game overs)
 * until you press backquote again, so you can replay a round without
 * re-arming it.
 */

/** Toggled by ` on the title screen. Not persisted across a page reload. */
let debugOn = false;

/** @returns {boolean} whether debug mode is currently on */
export function debugIsOn() {
  return debugOn;
}

/** `Digit0`..`Digit8` / `Numpad0`..`Numpad8` -> round number, or -1. */
function pressedRound(input) {
  for (let n = 0; n <= 8; n++) {
    if (input.isDown(`Digit${n}`) || input.isDown(`Numpad${n}`)) return n;
  }
  return -1;
}

/**
 * Poll this once per frame from the title screen's idle loop. It owns the
 * backquote toggle, the round select and the status line.
 *
 * @param {import('../context.js').Context} ctx
 */
export function debugTitleTick(ctx) {
  const { input, screen, state } = ctx;

  // Edge-detect the toggle so holding it does not flap the mode.
  const toggleDown = input.isDown(DEBUG_TOGGLE_KEY);
  if (toggleDown && !ctx.debugKeyWas) {
    debugOn = !debugOn;
    if (!debugOn) {
      ctx.debugRoundArmed = false;
      screen.writeNameTable(DEBUG_LINE, ' '.repeat(18)); // leave a stock title
    }
  }
  ctx.debugKeyWas = toggleDown;
  if (!debugOn) return;

  const n = pressedRound(input);
  if (n >= 0) {
    state.round = n;
    ctx.debugRoundArmed = true;
  }

  const label = ctx.debugRoundArmed
    ? `DEBUG ROUND ${state.round & 0x0f}`
    : 'DEBUG  0-8 ROUND';
  screen.writeNameTable(DEBUG_LINE, label.padEnd(18, ' '));
}

/** The toggle: backquote/tilde, never a game control. */
const DEBUG_TOGGLE_KEY = 'Backquote';

/**
 * Where the status line goes: low in the playfield, which the scroll paints
 * over the instant the game starts, so it can never be mistaken for the HUD.
 */
const DEBUG_LINE = 0x3aca;
