/**
 * Shared helpers for running the web port's modules under Node, so screens can
 * be verified as PNGs without a browser.
 */

import { readFile } from 'node:fs/promises';
import { deflateSync, inflateSync, crc32 } from 'node:zlib';
import { fileURLToPath } from 'node:url';
import path from 'node:path';

import { Screen } from '../../web/src/screen.js';
import { Assets, decodePngPayload } from '../../web/src/assets.js';
import { Input } from '../../web/src/input.js';
import { Sound } from '../../web/src/sound.js';
import { GameState } from '../../web/src/game/state.js';

export const ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..', '..');
export const ASSET_DIR = path.join(ROOT, 'web', 'assets');

function chunk(tag, payload) {
  const len = Buffer.alloc(4);
  len.writeUInt32BE(payload.length);
  const body = Buffer.concat([Buffer.from(tag, 'latin1'), payload]);
  const crc = Buffer.alloc(4);
  crc.writeUInt32BE(crc32(body) >>> 0);
  return Buffer.concat([len, body, crc]);
}

/** Encode an RGBA buffer as a PNG, nearest-neighbour scaled. */
export function encodePng(rgba, width, height, scale = 1) {
  const w = width * scale;
  const h = height * scale;
  const raw = Buffer.alloc(h * (1 + w * 3));
  let p = 0;
  for (let y = 0; y < h; y++) {
    raw[p++] = 0; // filter: none
    const row = ((y / scale) | 0) * width;
    for (let x = 0; x < w; x++) {
      const src = (row + ((x / scale) | 0)) * 4;
      raw[p++] = rgba[src];
      raw[p++] = rgba[src + 1];
      raw[p++] = rgba[src + 2];
    }
  }
  const ihdr = Buffer.alloc(13);
  ihdr.writeUInt32BE(w, 0);
  ihdr.writeUInt32BE(h, 4);
  ihdr[8] = 8;
  ihdr[9] = 2;
  return Buffer.concat([
    Buffer.from('89504e470d0a1a0a', 'hex'),
    chunk('IHDR', ihdr),
    chunk('IDAT', deflateSync(raw, { level: 9 })),
    chunk('IEND', Buffer.alloc(0)),
  ]);
}

export async function loadAssets(dir = ASSET_DIR) {
  const manifest = JSON.parse(await readFile(path.join(dir, 'manifest.json'), 'utf8'));
  const inflate = async (bytes) => new Uint8Array(inflateSync(bytes));
  const gfx = await decodePngPayload(
    new Uint8Array(await readFile(path.join(dir, manifest.gfx.file))),
    inflate,
    manifest.gfx.byteLength
  );
  const data = await decodePngPayload(
    new Uint8Array(await readFile(path.join(dir, manifest.data.file))),
    inflate,
    manifest.data.byteLength
  );
  return new Assets(manifest, gfx, data);
}

/** Build a Context with a detached Input (no DOM listeners). */
export async function makeContext() {
  const assets = await loadAssets();
  return {
    assets,
    rom: assets.rom,
    screen: new Screen(assets.palette),
    input: new Input(),
    sound: new Sound(assets.rom),
    state: new GameState(),
  };
}
