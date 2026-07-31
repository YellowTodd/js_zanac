/**
 * Headless render check for the web port's display model.
 *
 *   node tools/render_check.mjs [outdir]
 *
 * Loads the exported assets, drives web/src/screen.js directly (it has no DOM
 * dependency) and writes PNGs so the rasteriser can be eyeballed without a
 * browser.
 */

import { writeFile, mkdir } from 'node:fs/promises';
import { deflateSync, crc32 } from 'node:zlib';
import { fileURLToPath } from 'node:url';
import path from 'node:path';

import { Screen, SCREEN_W, SCREEN_H, COLS } from '../web/src/screen.js';
import { CHARSET_BLOCKS, LOGO_BLOCKS } from '../web/src/assets.js';
import { loadAssets } from './lib/headless.mjs';

const ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const ASSETS = path.join(ROOT, 'web', 'assets');

function chunk(tag, payload) {
  const len = Buffer.alloc(4);
  len.writeUInt32BE(payload.length);
  const body = Buffer.concat([Buffer.from(tag, 'latin1'), payload]);
  const crc = Buffer.alloc(4);
  crc.writeUInt32BE(crc32(body) >>> 0);
  return Buffer.concat([len, body, crc]);
}

/** Encode an RGBA buffer as a PNG, scaled up by an integer factor. */
function encodePng(rgba, width, height, scale) {
  const w = width * scale;
  const h = height * scale;
  const raw = Buffer.alloc(h * (1 + w * 3));
  let p = 0;
  for (let y = 0; y < h; y++) {
    raw[p++] = 0; // filter: none
    const srcRow = ((y / scale) | 0) * width;
    for (let x = 0; x < w; x++) {
      const src = (srcRow + ((x / scale) | 0)) * 4;
      raw[p++] = rgba[src];
      raw[p++] = rgba[src + 1];
      raw[p++] = rgba[src + 2];
    }
  }
  const ihdr = Buffer.alloc(13);
  ihdr.writeUInt32BE(w, 0);
  ihdr.writeUInt32BE(h, 4);
  ihdr[8] = 8; // bit depth
  ihdr[9] = 2; // truecolour
  return Buffer.concat([
    Buffer.from('89504e470d0a1a0a', 'hex'),
    chunk('IHDR', ihdr),
    chunk('IDAT', deflateSync(raw, { level: 9 })),
    chunk('IEND', Buffer.alloc(0)),
  ]);
}



function buildTestScreen(assets) {
  const screen = new Screen(assets.palette);
  assets.loadTiles(screen, [...CHARSET_BLOCKS, ...LOGO_BLOCKS]);
  screen.displayOn = true;
  screen.fillNameTable(0x20);

  // Rows 0-7: the whole 256-tile set, in order.
  for (let i = 0; i < 256; i++) screen.nameTable[i] = i;

  screen.writeText(1, 9, 'ABCDEFGHIJKLMNOPQRSTUVWXYZ 0123');
  screen.writeText(1, 10, 'SCORE 0123456   TOP    10000');
  screen.writeText(1, 11, 'TILE CODES ARE ASCII @ 1986');

  // Rows 13-14: the logo tiles the title screen uses (0xB0 onward).
  for (let i = 0; i < 61; i++) screen.nameTable[13 * COLS + i] = 0xb0 + i;

  // A spread of sprite patterns across the lower half.
  const colors = [15, 7, 9, 2, 11, 5, 13, 8];
  for (let i = 0; i < 8; i++) {
    screen.setSprite(i, 140, 16 + i * 28, i * 4, colors[i]);
  }
  // Second row of sprites, exercising the 4-per-line limit.
  for (let i = 0; i < 6; i++) {
    screen.setSprite(8 + i, 164, 40 + i * 12, (8 + i) * 4, 15);
  }
  return screen;
}

async function main() {
  const outdir = process.argv[2] ?? 'C:/Temp/zanac-gfx';
  await mkdir(outdir, { recursive: true });
  const assets = await loadAssets();

  const screen = buildTestScreen(assets);
  screen.render();
  await writeFile(
    path.join(outdir, 'render_test.png'),
    encodePng(screen.rgba, SCREEN_W, SCREEN_H, 3)
  );

  screen.spriteLimit = false;
  screen.render();
  await writeFile(
    path.join(outdir, 'render_test_nolimit.png'),
    encodePng(screen.rgba, SCREEN_W, SCREEN_H, 3)
  );

  console.log(`data payload retained ${assets.manifest.data.retainedBytes} data bytes`);
  console.log(`wrote render_test.png / render_test_nolimit.png -> ${outdir}`);
}

main();
