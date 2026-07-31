/**
 * Zanac display model - a native reimplementation of the TMS9918A Graphic II
 * (SCREEN 2) layout the game uses, not an emulation of the chip.
 *
 * The game keeps the VDP in one fixed configuration for its whole run
 * (see kb/guides/zanac-vdp-layout.md), so the model is fixed too:
 *   - 32x24 name table, 8x8 tiles
 *   - three 256-tile pattern/colour banks, one per screen third
 *   - 32 sprites, 16x16, unmagnified
 *
 * Rendering is pure: `render()` fills an RGBA buffer with no DOM involvement,
 * so the same code runs in the browser and in the headless PNG check
 * (tools/render_check.mjs).
 */

export const SCREEN_W = 256;
export const SCREEN_H = 192;
export const COLS = 32;
export const ROWS = 24;

export const TILES_PER_BANK = 256;
export const BANKS = 3;
export const BANK_BYTES = TILES_PER_BANK * 8;

/**
 * VRAM address of the name table (VDP R2 = 0x0E). Game code addresses screen
 * cells by their VRAM address throughout the knowledge base, so the port keeps
 * that convention via `writeNameTable`/`cellAt`.
 */
export const NAME_TABLE_BASE = 0x3800;

/** Sprite Y value that terminates the attribute list. */
export const SAT_TERMINATOR = 208;
/** Y values at or above this wrap to negative (sprite entering from the top). */
const SAT_Y_WRAP = 224;

const MAX_SPRITES = 32;
const SPRITES_PER_LINE = 4;

/** Pack an [r,g,b] triple the same way the RGBA byte buffer is laid out. */
function pack(rgb) {
  const bytes = new Uint8Array(4);
  const word = new Uint32Array(bytes.buffer);
  bytes[0] = rgb[0];
  bytes[1] = rgb[1];
  bytes[2] = rgb[2];
  bytes[3] = 0xff;
  return word[0];
}

export class Screen {
  /** @param {number[][]} palette 16 TMS9918A colours as [r,g,b] */
  constructor(palette) {
    this.pal32 = new Uint32Array(palette.map(pack));

    // Tile graphics: three banks, one per screen third (rows 0-7, 8-15, 16-23).
    this.patterns = new Uint8Array(BANKS * BANK_BYTES);
    this.colors = new Uint8Array(BANKS * BANK_BYTES);
    this.nameTable = new Uint8Array(COLS * ROWS);

    // Sprites: 64 patterns of 32 bytes, 32 attribute entries of 4 bytes.
    this.spriteGen = new Uint8Array(2048);
    this.sat = new Uint8Array(MAX_SPRITES * 4);

    /** Backdrop colour (VDP R7 low nibble); also shows through colour 0. */
    this.backdrop = 1;
    /** Display enable (VDP R1 BL). While false the screen is pure backdrop. */
    this.displayOn = false;
    /** Honour the hardware's 4-sprites-per-line limit. */
    this.spriteLimit = true;

    this.rgba = new Uint8ClampedArray(SCREEN_W * SCREEN_H * 4);
    this.px = new Uint32Array(this.rgba.buffer);

    this._lineCount = new Uint8Array(SCREEN_H);
    this._sprites = [];
    for (let i = 0; i < MAX_SPRITES; i++) {
      this._sprites.push({ top: 0, x: 0, color: 0, base: 0, rows: new Uint8Array(16) });
    }

    this.hideSprites();
  }

  /** Park every sprite off-list, the way `init_screen_mode` (0x428A) does. */
  hideSprites() {
    for (let i = 0; i < MAX_SPRITES; i++) this.sat[i * 4] = SAT_TERMINATOR;
  }

  /** Write one sprite attribute entry. `y` is the raw VDP value. */
  setSprite(slot, y, x, pattern, color) {
    const i = slot * 4;
    this.sat[i] = y;
    this.sat[i + 1] = x;
    this.sat[i + 2] = pattern;
    this.sat[i + 3] = color;
  }

  fillNameTable(tile = 0x20) {
    this.nameTable.fill(tile);
  }

  /** Write an ASCII string into the name table (tile codes are ASCII). */
  writeText(col, row, text) {
    let p = row * COLS + col;
    for (let i = 0; i < text.length; i++) this.nameTable[p++] = text.charCodeAt(i) & 0xff;
  }

  /** Name-table index for a VRAM address, the way `tile_to_vram_addr` maps it. */
  cellAt(vramAddr) {
    return vramAddr - NAME_TABLE_BASE;
  }

  /**
   * Write tiles at a VRAM name-table address, the equivalent of
   * `SETWRT` + a run of data-port writes.
   * @param {number} vramAddr
   * @param {string|ArrayLike<number>} tiles ASCII string or tile codes
   */
  writeNameTable(vramAddr, tiles) {
    let p = vramAddr - NAME_TABLE_BASE;
    if (typeof tiles === 'string') {
      for (let i = 0; i < tiles.length; i++) this.nameTable[p++] = tiles.charCodeAt(i) & 0xff;
    } else {
      for (let i = 0; i < tiles.length; i++) this.nameTable[p++] = tiles[i];
    }
  }

  render() {
    if (!this.displayOn) {
      this.px.fill(this.pal32[this.backdrop]);
      return this.rgba;
    }
    this._renderTiles();
    this._renderSprites();
    return this.rgba;
  }

  _renderTiles() {
    const { patterns, colors, nameTable, pal32, px, backdrop } = this;
    for (let row = 0; row < ROWS; row++) {
      const bankOff = (row >> 3) * BANK_BYTES;
      for (let col = 0; col < COLS; col++) {
        const off = bankOff + nameTable[row * COLS + col] * 8;
        for (let r = 0; r < 8; r++) {
          const bits = patterns[off + r];
          const attr = colors[off + r];
          const fg = pal32[(attr >> 4) || backdrop];
          const bg = pal32[(attr & 0x0f) || backdrop];
          let p = (row * 8 + r) * SCREEN_W + col * 8;
          px[p] = bits & 0x80 ? fg : bg;
          px[p + 1] = bits & 0x40 ? fg : bg;
          px[p + 2] = bits & 0x20 ? fg : bg;
          px[p + 3] = bits & 0x10 ? fg : bg;
          px[p + 4] = bits & 0x08 ? fg : bg;
          px[p + 5] = bits & 0x04 ? fg : bg;
          px[p + 6] = bits & 0x02 ? fg : bg;
          px[p + 7] = bits & 0x01 ? fg : bg;
        }
      }
    }
  }

  _renderSprites() {
    const { sat, spriteGen, pal32, px } = this;
    const lineCount = this._lineCount.fill(0);
    const list = this._sprites;
    let count = 0;

    for (let i = 0; i < MAX_SPRITES; i++) {
      const y = sat[i * 4];
      if (y === SAT_TERMINATOR) break;
      const sp = list[count++];
      sp.top = y >= SAT_Y_WRAP ? y - 255 : y + 1;
      const attr = sat[i * 4 + 3];
      sp.x = attr & 0x80 ? sat[i * 4 + 1] - 32 : sat[i * 4 + 1];
      sp.color = attr & 0x0f;
      sp.base = (sat[i * 4 + 2] & 0xfc) * 8;

      // Lower slot numbers win the per-line budget; transparent sprites still
      // consume it, exactly as the hardware counts them.
      for (let r = 0; r < 16; r++) {
        const line = sp.top + r;
        if (line < 0 || line >= SCREEN_H) {
          sp.rows[r] = 0;
          continue;
        }
        sp.rows[r] = !this.spriteLimit || lineCount[line] < SPRITES_PER_LINE ? 1 : 0;
        lineCount[line]++;
      }
    }

    // Paint back-to-front so slot 0 ends up on top.
    for (let s = count - 1; s >= 0; s--) {
      const sp = list[s];
      if (sp.color === 0) continue; // transparent: occupies a slot, draws nothing
      const rgb = pal32[sp.color];
      for (let r = 0; r < 16; r++) {
        if (!sp.rows[r]) continue;
        const rowBase = (sp.top + r) * SCREEN_W;
        for (let half = 0; half < 2; half++) {
          const bits = spriteGen[sp.base + half * 16 + r];
          if (bits === 0) continue;
          const x0 = sp.x + half * 8;
          for (let c = 0; c < 8; c++) {
            if (!((bits >> (7 - c)) & 1)) continue;
            const x = x0 + c;
            if (x < 0 || x >= SCREEN_W) continue;
            px[rowBase + x] = rgb;
          }
        }
      }
    }
  }
}
