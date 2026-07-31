import { KEY_PAUSE, KEY_SELECT } from '../input.js';

/**
 * Frame-scheduling helpers.
 *
 * The engine is written as blocking code that calls `wait_frames` (0x5BEC) or
 * `wait_one_frame` (0x4306) to sync with the VBLANK interrupt. The port keeps
 * that structure by writing game routines as generators: every `yield` hands a
 * finished frame back to the driver in main.js.
 */

/** `wait_frames` (0x5BEC) - block for `count` frames. */
export function* waitFrames(count) {
  for (let i = 0; i < count; i++) yield;
}

/** `wait_one_frame` (0x4306). */
export function* waitOneFrame() {
  yield;
}

/** The caption's five name-table cells (0x396A) and its literal (0x4E40). */
const PAUSE_VRAM = 0x396a;
const PAUSE_TEXT = 'PAUSE';

/**
 * `pause_handler` (0x4DA5), run once per frame from `gameplay_frame_loop`.
 *
 * MSX matrix keys are **active low**, which flips the sense of every test
 * here: `BIT 4,A / JR Z` at 0x4DAD means "STOP *is* pressed". Bit 7 of
 * 0xE118 is a latch that stops one press pausing repeatedly, and bits 0-4 of
 * the same byte are the blink counter.
 *
 * **SELECT is a modifier, not a second pause key** (0x4DB7): STOP alone gives
 * the blinking PAUSE caption, STOP together with SELECT gives a silent hold
 * that leaves the display untouched.
 *
 * Getting out takes a *fresh* press - 0x4E30 only arms the exit once STOP has
 * been released, so holding the key does not immediately unpause. The PSG is
 * muted through 0x5208 rather than stopped, so the music picks up where it
 * left off.
 *
 * @param {import('../context.js').Context} ctx
 */
export function* pauseHandler(ctx) {
  const { input, screen, sound } = ctx;

  if (!input.isDown(KEY_PAUSE)) {
    ctx.pauseLatch = false; // 0x4DB1: released - re-arm
    return;
  }
  if (ctx.pauseLatch) return; // 0x4DB6: this press already handled

  const quiet = input.isDown(KEY_SELECT); // 0x4DB7
  sound.setMuted(true); // 0x5208

  // 0x4DC5: stash what the caption is about to cover.
  const saved = [];
  if (!quiet) {
    for (let i = 0; i < PAUSE_TEXT.length; i++) {
      saved.push(screen.nameTable[PAUSE_VRAM - 0x3800 + i]);
    }
  }

  let counter = 0;
  let armed = false;
  for (;;) {
    // 0x4DD5: VRAM is touched only when the low nibble wraps, and bit 4 picks
    // which of the two images to show - a 32-frame blink.
    if (!quiet && (counter & 0x0f) === 0) {
      screen.writeNameTable(PAUSE_VRAM, counter & 0x10 ? saved : PAUSE_TEXT);
    }
    yield; // 0x4E32 wait_one_frame
    counter = (counter + 1) & 0x1f; // 0x4E10

    const down = input.isDown(KEY_PAUSE);
    if (armed) {
      if (down) break; // 0x4E26: a fresh press ends it
    } else if (!down) {
      armed = true; // 0x4E30: released, so the next press counts
    }
  }

  if (!quiet) screen.writeNameTable(PAUSE_VRAM, saved); // 0x4DFC
  sound.setMuted(false); // 0x520E
  ctx.pauseLatch = true; // the exiting press must not pause again
}
