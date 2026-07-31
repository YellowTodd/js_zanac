/**
 * Headless capture of the title sequence.
 *
 *   node tools/title_check.mjs [outdir]
 *
 * Runs the real `coldStart` generator frame by frame and writes a PNG at the
 * frames listed in CAPTURES, so the logo swirl can be checked against the
 * original without an emulator.
 */

import { writeFile, mkdir } from 'node:fs/promises';
import path from 'node:path';

import { SCREEN_W, SCREEN_H } from '../web/src/screen.js';
import { coldStart } from '../web/src/game/flow.js';
import { encodePng, makeContext } from './lib/headless.mjs';

/** frame -> file label. The swirl advances one path step every 2 frames. */
const CAPTURES = new Map([
  [3, '00-display-on'],
  [20, '01-swirl-early'],
  [46, '02-swirl-mid'],
  [78, '03-swirl-late'],
  [130, '04-settled'],
  [160, '05-idle'],
]);

async function main() {
  const outdir = process.argv[2] ?? 'C:/Temp/zanac-gfx';
  await mkdir(outdir, { recursive: true });

  const ctx = await makeContext();
  const task = coldStart(ctx);
  const total = Math.max(...CAPTURES.keys());

  for (let frame = 0; frame <= total; frame++) {
    task.next();
    ctx.state.frame++;
    const label = CAPTURES.get(frame);
    if (!label) continue;
    ctx.screen.render();
    const file = path.join(outdir, `title_${label}.png`);
    await writeFile(file, encodePng(ctx.screen.rgba, SCREEN_W, SCREEN_H, 3));
    console.log(`frame ${String(frame).padStart(3)}  ->  ${path.basename(file)}`);
  }
  console.log(`sound events requested: ${ctx.sound.drainLog().join(', ')}`);
}

main();
