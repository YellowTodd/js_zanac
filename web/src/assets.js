/**
 * Asset loading for the Zanac web port.
 *
 * Two files, both produced by tools/export_assets.py:
 *   gfx.png   the nine graphics blocks, already RLE-decoded
 *   data.png  a 32 KB address-identity image of the cartridge's *data* bytes
 *             (Z80 code zeroed), so game code can address tables with the
 *             same 0xNNNN constants the knowledge base uses
 */

import { BANKS, BANK_BYTES } from './screen.js';

export const ROM_BASE = 0x4000;
export const ROM_END = 0xc000;

/** Address-space view over the data payload. */
export class DataRom {
  /** @param {Uint8Array} bytes */
  constructor(bytes) {
    if (bytes.length !== ROM_END - ROM_BASE) {
      throw new Error(`data payload must be ${ROM_END - ROM_BASE} bytes, got ${bytes.length}`);
    }
    this.bytes = bytes;
  }

  /** @param {number} addr absolute Z80 address */
  byte(addr) {
    return this.bytes[addr - ROM_BASE];
  }

  /** Little-endian 16-bit read, as `LD HL,(nn)` would do. */
  word(addr) {
    const i = addr - ROM_BASE;
    return this.bytes[i] | (this.bytes[i + 1] << 8);
  }

  /** Signed byte, for the many delta/velocity tables. */
  sbyte(addr) {
    return (this.bytes[addr - ROM_BASE] << 24) >> 24;
  }

  slice(addr, length) {
    const i = addr - ROM_BASE;
    return this.bytes.subarray(i, i + length);
  }
}

/**
 * Extract the raw payload from one of the exporter's PNG containers.
 *
 * The format is fully under our control (tools/export_assets.py). The exact
 * bytes ride in a private ancillary chunk `zaNc` (a zlib stream), so the
 * visible image can be a human-readable tilesheet; viewers ignore the chunk.
 * `inflate` is DecompressionStream('deflate') in the browser, node:zlib in
 * the headless harness. No canvas involved, so there is no premultiplied-
 * alpha hazard. Legacy containers without `zaNc` fall back to unpacking the
 * IDAT pixels (3 payload bytes per RGB pixel, filter 0).
 *
 * @param {Uint8Array} png
 * @param {(zlibBytes: Uint8Array) => Promise<Uint8Array>} inflate
 * @param {number} byteLength
 */
export async function decodePngPayload(png, inflate, byteLength) {
  const view = new DataView(png.buffer, png.byteOffset, png.byteLength);
  let width = 0;
  const idat = [];
  let payloadChunk = null;
  let offset = 8; // signature
  while (offset < png.length) {
    const size = view.getUint32(offset);
    const tag = String.fromCharCode(...png.subarray(offset + 4, offset + 8));
    const body = png.subarray(offset + 8, offset + 8 + size);
    if (tag === 'IHDR') {
      width = view.getUint32(offset + 8);
      if (png[offset + 8 + 8] !== 8 || png[offset + 8 + 9] !== 2) {
        throw new Error('unexpected PNG format (want 8-bit RGB)');
      }
    } else if (tag === 'zaNc') payloadChunk = body;
    else if (tag === 'IDAT') idat.push(body);
    else if (tag === 'IEND') break;
    offset += 12 + size;
  }
  if (payloadChunk) {
    const raw = await inflate(payloadChunk);
    if (raw.length < byteLength) {
      throw new Error(`payload chunk too short: ${raw.length} < ${byteLength}`);
    }
    return raw.subarray(0, byteLength);
  }
  const zlibData = new Uint8Array(idat.reduce((n, c) => n + c.length, 0));
  let at = 0;
  for (const c of idat) {
    zlibData.set(c, at);
    at += c.length;
  }
  const raw = await inflate(zlibData);
  const stride = 1 + width * 3;
  const out = new Uint8Array(byteLength);
  let src = 0;
  let dst = 0;
  while (dst < byteLength && src < raw.length) {
    if (raw[src] !== 0) throw new Error('unexpected PNG row filter');
    const take = Math.min(width * 3, byteLength - dst);
    out.set(raw.subarray(src + 1, src + 1 + take), dst);
    dst += take;
    src += stride;
  }
  return out;
}

/** Browser-side zlib inflate via DecompressionStream. */
async function inflateBrowser(bytes) {
  const stream = new Blob([bytes]).stream().pipeThrough(new DecompressionStream('deflate'));
  return new Uint8Array(await new Response(stream).arrayBuffer());
}

export class Assets {
  /**
   * @param {any} manifest parsed manifest.json
   * @param {Uint8Array} gfx
   * @param {Uint8Array} data
   */
  constructor(manifest, gfx, data) {
    this.manifest = manifest;
    this.gfx = gfx;
    this.rom = new DataRom(data);
    this.palette = manifest.palette;
    /** @type {Map<string, any>} */
    this.blocks = new Map(manifest.gfx.blocks.map((b) => [b.name, b]));
  }

  static async load(baseUrl = './assets/') {
    const grab = async (name, asJson = false) => {
      const res = await fetch(baseUrl + name);
      if (!res.ok) throw new Error(`cannot load ${name}: ${res.status}`);
      return asJson ? res.json() : new Uint8Array(await res.arrayBuffer());
    };
    const manifest = await grab('manifest.json', true);
    const [gfxPng, dataPng] = await Promise.all([
      grab(manifest.gfx.file),
      grab(manifest.data.file),
    ]);
    const gfx = await decodePngPayload(gfxPng, inflateBrowser, manifest.gfx.byteLength);
    const data = await decodePngPayload(dataPng, inflateBrowser, manifest.data.byteLength);
    return new Assets(manifest, gfx, data);
  }

  blockData(name) {
    const b = this.blocks.get(name);
    if (!b) throw new Error(`unknown graphics block: ${name}`);
    return this.gfx.subarray(b.offset, b.offset + b.length);
  }

  /**
   * Copy graphics blocks into a Screen, mirroring what the ROM loaders do.
   * Pattern and colour blocks go into all three banks identically, because
   * load_charset_sprites / load_bg_tiles / load_logo_tiles each call
   * decompress_block three times with HL += 0x800.
   *
   * @param {import('./screen.js').Screen} screen
   * @param {string[]} names
   */
  loadTiles(screen, names) {
    for (const name of names) {
      const block = this.blocks.get(name);
      if (!block) throw new Error(`unknown graphics block: ${name}`);
      const data = this.blockData(name);
      if (block.kind === 'sprite') {
        screen.spriteGen.set(data, 0);
        continue;
      }
      const dst = block.kind === 'pattern' ? screen.patterns : screen.colors;
      for (let bank = 0; bank < BANKS; bank++) {
        dst.set(data, bank * BANK_BYTES + block.tile * 8);
      }
    }
  }
}

/** Blocks loaded by `load_charset_sprites` (0x5CA5) - the always-present set. */
export const CHARSET_BLOCKS = ['charset_bitmap', 'charset_colors', 'sprite_patterns'];
/** Blocks loaded by `load_logo_tiles` (0x5C3C) - title screen only. */
export const LOGO_BLOCKS = ['logo_bitmap', 'logo_colors'];
/** Blocks loaded by `load_bg_tiles` (0x5C60) - late-stage terrain. */
export const BG_LATE_BLOCKS = [
  'bg_late_bitmap_a',
  'bg_late_colors_a',
  'bg_late_bitmap_b',
  'bg_late_colors_b',
];
