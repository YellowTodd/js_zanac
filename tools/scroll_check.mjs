/**
 * Headless capture of the scrolling playfield.
 *
 *   node tools/scroll_check.mjs [outdir] [round]
 *
 * Drives the real game flow through the title screen into gameplay, then
 * writes PNGs at intervals so the terrain can be inspected as it scrolls.
 */

import { writeFile, mkdir } from 'node:fs/promises';
import path from 'node:path';

import { SCREEN_W, SCREEN_H } from '../web/src/screen.js';
import { coldStart } from '../web/src/game/flow.js';
import { encodePng, makeContext } from './lib/headless.mjs';

const TITLE_FRAMES = 200;
const CAPTURES = [0, 30, 90, 180, 360, 600];

function press(input, code, down) {
  if (down) {
    input.keys.add(code);
    input._held.add(code);
  } else {
    input.keys.delete(code);
    input._held.delete(code);
  }
  input._recompute();
}

async function main() {
  const outdir = process.argv[2] ?? 'C:/Temp/zanac-gfx';
  const round = Number(process.argv[3] ?? 1);
  await mkdir(outdir, { recursive: true });

  const ctx = await makeContext();
  const task = coldStart(ctx);

  for (let i = 0; i < TITLE_FRAMES; i++) task.next();
  press(ctx.input, 'Space', true);
  for (let i = 0; i < 4; i++) task.next();
  press(ctx.input, 'Space', false);
  if (round !== 1) {
    ctx.state.round = round;
    ctx.state.streamPtr = ctx.rom.word(0x945c + 2 * (8 - round));
  }
  for (let i = 0; i < 8; i++) task.next();

  const last = CAPTURES[CAPTURES.length - 1];
  let next = 0;
  for (let frame = 0; frame <= last; frame++) {
    if (CAPTURES[next] === frame) {
      ctx.screen.render();
      const file = path.join(outdir, `scroll_r${round}_${String(frame).padStart(4, '0')}.png`);
      await writeFile(file, encodePng(ctx.screen.rgba, SCREEN_W, SCREEN_H, 3));
      console.log(
        `frame ${String(frame).padStart(4)}  mapRow ${String(ctx.scroll.levelRow).padStart(4)}  ` +
          `nextCmdRow ${String(ctx.scroll.nextCmdRow).padStart(5)}  ` +
          `pc 0x${ctx.scroll.streamPtr.toString(16)}  speed ${ctx.scroll.speed}  ` +
          `-> ${path.basename(file)}`
      );
      next++;
    }
    task.next();
  }
}

main();
