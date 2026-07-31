/**
 * Browser entry point: build the context, run the game generator one step per
 * frame, and blit the rendered screen to the canvas.
 */

import { Screen, SCREEN_W, SCREEN_H } from './screen.js';
import { Assets } from './assets.js';
import { Input } from './input.js';
import { Sound } from './sound.js';
import { PsgAudio } from './audio.js';
import { GameState } from './game/state.js';
import { coldStart } from './game/flow.js';

/** The MSX1 NTSC refresh the engine is timed against. */
const FRAME_MS = 1000 / 59.92;
/** Never simulate more than this many frames after a stall (tab in background). */
const MAX_CATCHUP = 4;

function fitCanvas(canvas) {
  const scale = Math.max(
    1,
    Math.min(
      Math.floor(window.innerWidth / SCREEN_W),
      Math.floor((window.innerHeight - 8) / SCREEN_H)
    )
  );
  canvas.style.width = `${SCREEN_W * scale}px`;
  canvas.style.height = `${SCREEN_H * scale}px`;
}

async function boot() {
  const canvas = /** @type {HTMLCanvasElement} */ (document.getElementById('screen'));
  const status = document.getElementById('status');
  canvas.width = SCREEN_W;
  canvas.height = SCREEN_H;
  const gfx = canvas.getContext('2d', { alpha: false });
  gfx.imageSmoothingEnabled = false;

  const assets = await Assets.load();
  const screen = new Screen(assets.palette);
  const input = new Input();
  input.attach(window);

  /** @type {import('./context.js').Context} */
  const ctx = {
    assets,
    rom: assets.rom,
    screen,
    input,
    sound: new Sound(assets.rom),
    state: new GameState(),
  };

  const frame = gfx.createImageData(SCREEN_W, SCREEN_H);
  const task = coldStart(ctx);

  fitCanvas(canvas);
  window.addEventListener('resize', () => fitCanvas(canvas));
  if (status) status.textContent = 'arrows/WASD move - SPACE or SHIFT shot - Z fire - ESC continue';

  // WebAudio needs a user gesture; create the backend on the first one. Any
  // gesture counts, not just a keypress - a player who clicks the canvas
  // before touching the keyboard would otherwise never get sound at all.
  let audio = null;
  const GESTURES = ['keydown', 'pointerdown', 'touchstart'];
  const startAudio = () => {
    if (!audio) audio = new PsgAudio();
    for (const ev of GESTURES) window.removeEventListener(ev, startAudio);
  };
  for (const ev of GESTURES) window.addEventListener(ev, startAudio);

  let carry = 0;
  let last = performance.now();

  const tick = (now) => {
    requestAnimationFrame(tick);
    carry += now - last;
    last = now;
    let steps = Math.min(MAX_CATCHUP, Math.floor(carry / FRAME_MS));
    if (steps <= 0) return;
    carry -= steps * FRAME_MS;

    while (steps-- > 0) {
      task.next();
      ctx.sound.tick();
      ctx.state.frame++;
    }

    if (audio && ctx.sound.engine) audio.update(ctx.sound.engine.regs);
    frame.data.set(screen.render());
    gfx.putImageData(frame, 0, 0);
  };
  requestAnimationFrame(tick);
}

boot().catch((err) => {
  const status = document.getElementById('status');
  if (status) status.textContent = `boot failed: ${err.message}`;
  throw err;
});
