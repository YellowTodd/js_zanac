/**
 * Score and status display.
 * Mirrors the 0x49xx HUD routines (kb/symbols/0x4900-hud/).
 */

/** VRAM name-table slots, from kb/guides/zanac-vdp-layout.md. */
export const VRAM_SCORE = 0x3809;
export const VRAM_TOPSCORE = 0x3815;
/** `render_topscore_row2` (0x49A7): the status panel's TOP row. */
const TOPSCORE_ROW2 = 0x38b8;
export const VRAM_SCORE_LABEL = 0x3803;
export const VRAM_TOP_LABEL = 0x3811;

/**
 * `render_score_bcd` (0x49B5): 3 BCD bytes -> 7 tiles.
 *
 * The six BCD digits are emitted high-nibble first from the top byte down,
 * with leading zeros blanked to spaces, and a literal '0' is always appended
 * (0x49D6) - scores are stored in units of ten.
 *
 * @param {import('../screen.js').Screen} screen
 * @param {Uint8Array} bcd [lo, mid, hi]
 * @param {number} vramAddr
 */
export function renderScoreBcd(screen, bcd, vramAddr) {
  const tiles = new Uint8Array(7);
  let seen = false;
  for (let i = 0; i < 6; i++) {
    const byte = bcd[2 - (i >> 1)];
    const digit = (i & 1) === 0 ? byte >> 4 : byte & 0x0f;
    if (digit !== 0) seen = true;
    tiles[i] = seen ? 0x30 + digit : 0x20;
  }
  tiles[6] = 0x30;
  screen.writeNameTable(vramAddr, tiles);
}

/**
 * `compare_save_hiscore` (0x4ACE): three BCD bytes compared high to low;
 * a winning score is copied over the top score.
 * @param {import('./state.js').GameState} state
 */
export function compareSaveHiscore(state) {
  for (let i = 2; i >= 0; i--) {
    if (state.score[i] > state.topScore[i]) {
      state.topScore.set(state.score);
      return;
    }
    if (state.score[i] < state.topScore[i]) return;
  }
}

/** `render_lives_score` (0x4996): current score, then top score. */
export function renderLivesScore(screen, state) {
  renderScoreBcd(screen, state.score, VRAM_SCORE);
  renderScoreBcd(screen, state.topScore, VRAM_TOPSCORE);
}

/** `score_award_table` (0x4AEA): 3-byte BCD point values, indexed by idx*3. */
const SCORE_AWARD_TABLE = 0x4aea;

/** One byte of BCD addition, the `ADD A,x / DAA` pair the engine uses. */
function bcdAddByte(a, b, carryIn) {
  let lo = (a & 0x0f) + (b & 0x0f) + carryIn;
  let carry = 0;
  if (lo > 9) {
    lo -= 10;
    carry = 1;
  }
  let hi = (a >> 4) + (b >> 4) + carry;
  carry = 0;
  if (hi > 9) {
    hi -= 10;
    carry = 1;
  }
  return { value: ((hi << 4) | lo) & 0xff, carry };
}

/**
 * `add_score` (0x4A74): BCD-add `score_award_table[index]` to the player score.
 *
 * The score is three BCD bytes low-to-high, and the display appends a literal
 * '0', so an award of index 13 ("1000" in the table) shows as 10000.
 *
 * @param {import('./state.js').GameState} state
 * @param {import('../assets.js').DataRom} rom
 * @param {number} index award index, e.g. from `structure_award_index_table`
 */
export function addScore(state, rom, index, ctx) {
  const entry = SCORE_AWARD_TABLE + index * 3;
  let carry = 0;
  for (let i = 0; i < 3; i++) {
    const sum = bcdAddByte(state.score[i], rom.byte(entry + i), carry);
    state.score[i] = sum.value;
    carry = sum.carry;
  }
  if (carry) state.score.fill(0x99); // 0x4A9A: peg at 999999 rather than wrap
  checkTopScore(state, ctx); // 0x4A94 -> 0x49F0
  awardExtends(state, ctx); // 0x4A97 -> 0x4A26
}

/** 3-byte little-endian BCD compare: is `a` >= `b`? */
function bcdAtLeast(a, b) {
  for (let i = 2; i >= 0; i--) {
    if (a[i] !== b[i]) return a[i] > b[i];
  }
  return true;
}

/**
 * 0x49F0's tail: the first time the score passes the top score, latch bit 6
 * of 0xE114 and play the record jingle (event 9). Bit 7 suppresses the jingle,
 * and 0xE102 bit 2 - set while the credits roll - suppresses it too.
 */
function checkTopScore(state, ctx) {
  if (!bcdAtLeast(state.score, state.topScore)) return; // 0x4A02 RET C
  if (state.recordFlags & 0x40) return; // 0x4A0E: already latched
  if (state.recordFlags & 0x80) return; // 0x4A11: jingle disabled
  state.recordFlags |= 0x40;
  if (ctx && ctx.sound && !(state.flowFlags & 0x04)) ctx.sound.playEvent(9);
}

/**
 * `LAB_4A26` (0x4A26): the **extra life**. While the score has reached the
 * threshold at 0xE111, hand out a life, advance the threshold and go round
 * again - a single big award can therefore pay out more than once.
 *
 * The first threshold is 0x2000 and is special-cased at 0x4A3F: it jumps
 * straight to 0x6000 rather than adding. After that each award adds 0x6000,
 * so the sequence is 20000, 60000, 120000, 180000, ... in displayed points.
 */
function awardExtends(state, ctx) {
  for (let guard = 0; guard < 16; guard++) {
    if (!bcdAtLeast(state.score, state.extendAt)) return; // 0x4A35 RET C
    if (state.extendAt[2] === 0 && state.extendAt[1] === 0x20) {
      state.extendAt[1] = 0x60; // 0x4A43: 20000 -> 60000
    } else {
      const mid = bcdAddByte(state.extendAt[1], 0x60, 0); // 0x4A48
      state.extendAt[1] = mid.value;
      state.extendAt[2] = bcdAddByte(state.extendAt[2], 0, mid.carry).value;
    }
    if (state.lives >= 0xff) return; // 0x4A56: saturate rather than wrap
    state.lives++; // 0x4A55
    if (ctx && ctx.sound && !(state.flowFlags & 0x04)) ctx.sound.playEvent(8);
  }
}

/**
 * `score_display_update` (0x4AA5), once per frame. Until the top score is
 * beaten this does nothing; afterwards 0xE114 free-runs and its bit 2 blinks
 * the TOP row on and off - the "new record" flash.
 *
 * @param {import('../screen.js').Screen} screen
 * @param {import('./state.js').GameState} state
 */
export function scoreDisplayUpdate(screen, state) {
  if ((state.recordFlags & 0x40) === 0) return; // 0x4AAA
  // 0x4AAB: `DE = 0x38B8` - the **panel's** TOP row, not the title screen's
  // 0x3815. And what it shows is the live **score**, because beating the
  // record promotes your score into that slot (0x4A03).
  if (state.recordFlags & 0x04) {
    renderScoreBcd(screen, state.score, TOPSCORE_ROW2);
  } else {
    screen.writeNameTable(TOPSCORE_ROW2, ' '.repeat(7)); // 0x4ABA FILVRM
  }
  state.recordFlags = (state.recordFlags + 1) & 0xff; // 0x4ACC
}

/** The static header labels written by `title_intro_seq` (0x5A24/0x5A30). */
export function drawScoreLabels(screen) {
  screen.writeNameTable(VRAM_SCORE_LABEL, 'SCORE');
  screen.writeNameTable(VRAM_TOP_LABEL, 'TOP');
}

// --------------------------------------------------------------------------
// Right-hand status panel (columns 24-31)
// --------------------------------------------------------------------------

/** Separator rows drawn by draw_hud_label_str (0x4BC7): tiles 01 02x6 01. */
const PANEL_SEPARATORS = [0x3818, 0x3878, 0x38d8, 0x3938, 0x3af8];
const SEPARATOR_TILES = [0x01, 0x02, 0x02, 0x02, 0x02, 0x02, 0x02, 0x01];
/** Vertical border strip (0x4BDF loop): 14 rows from 0x3958, tiles 03 .. 03. */
const STRIP_BASE = 0x3958;
const STRIP_ROWS = 14;
const STRIP_TILES = [0x03, 0x20, 0x20, 0x20, 0x20, 0x20, 0x20, 0x03];

/**
 * `draw_hud_labels` (0x4BD4): the static right-panel furniture, drawn once at
 * screen init. ROM order: border strip, then the five labels, then the
 * horizontal separators.
 */
export function drawHudPanel(screen) {
  let addr = STRIP_BASE;
  for (let i = 0; i < STRIP_ROWS; i++, addr += 0x20) {
    screen.writeNameTable(addr, STRIP_TILES);
  }
  screen.writeNameTable(0x38f9, 'SCORE');
  screen.writeNameTable(0x3899, 'TOP');
  screen.writeNameTable(0x3999, 'LEVEL');
  screen.writeNameTable(0x3959, 'ZANAC'); // the lives row
  screen.writeNameTable(0x39f9, 'ROUND');
  for (const sep of PANEL_SEPARATORS) screen.writeNameTable(sep, SEPARATOR_TILES);
  screen.writeNameTable(ALC_LABEL_ADDR, 'ALC'); // 0xBFD6, see drawAlcReadout
}

/** `base_encounter_ctrl` (0xBFD6) writes these two panel rows. */
const ALC_LABEL_ADDR = 0x3839;
const ALC_VALUE_ADDR = 0x3859;

/**
 * The **ALC debug readout that shipped in the retail ROM** (0xBFD6).
 *
 * `vdp_set_addr_write` (0x5C25) prints the NUL-terminated string that follows
 * the call - the bytes at 0xBFDC are `41 4C 43 00`, literally **"ALC"** - and
 * then `render_hex_byte` (0x4C74) writes 0xE12E, 0xE132 and 0xE130 as six hex
 * digits on the row below. The disassembly currently renders that string as
 * `LD B,C / LD C,H / LD B,E / NOP`, which is why it was missed.
 *
 * The ROM refreshes it from the tails of `inc_encounter_a` / `dec_encounter_a`
 * / `SUB_bfc8` / `dec_encounter_b` and once per round transition; drawing it
 * every frame is indistinguishable and much simpler.
 *
 * @param {import('../screen.js').Screen} screen
 * @param {import('./spawn.js').SpawnState} spawn
 */
export function drawAlcReadout(screen, spawn) {
  if (!spawn) return;
  const hex = (v) => {
    const d = (n) => (n < 10 ? 0x30 + n : 0x41 + n - 10);
    return [d((v >> 4) & 0x0f), d(v & 0x0f)];
  };
  screen.writeNameTable(ALC_VALUE_ADDR, [
    ...hex(spawn.accHi), // 0xE12E
    ...hex(spawn.posBias), // 0xE132
    ...hex(spawn.encounter), // 0xE130
  ]);
}

/** `write_digit_to_vram` (0x4B83): value as two tiles, leading space for <10. */
function writeTwoDigits(screen, vramAddr, value) {
  const tens = (value / 10) | 0;
  screen.writeNameTable(vramAddr, [tens ? 0x30 + tens : 0x20, 0x30 + (value % 10)]);
}

/**
 * `LAB_4B8D` (0x4B8D): **three** tiles with leading zeros blanked. The lives
 * counter uses this while the level and round use the two-tile form, and
 * because all three end at column 28 their values line up in one column - the
 * panel's look in the original.
 */
function writeThreeDigits(screen, vramAddr, value) {
  const h = (value / 100) | 0;
  const t2 = ((value / 10) | 0) % 10;
  screen.writeNameTable(vramAddr, [
    h ? 0x30 + h : 0x20,
    h || t2 ? 0x30 + t2 : 0x20,
    0x30 + (value % 10),
  ]);
}

/**
 * `update_status_bar` (0x4C4D) plus the row-2 score renders it falls through
 * from: round -> 0x3A1B, shot level -> 0x39BB, lives-1 -> 0x397A, and the
 * score/top-score values inside the panel (0x3918 / 0x38B8).
 */
export function updateStatusBar(screen, state, player) {
  writeTwoDigits(screen, 0x3a1b, state.round); // 0x4C6E, cols 27-28
  writeTwoDigits(screen, 0x39bb, player ? player.shotLevel : 0); // 0x4C53
  // 0x4C5F: the ROM renders **lives - 1** and skips the row entirely at 0,
  // through the three-tile form at columns 26-28.
  if (state.lives > 0) writeThreeDigits(screen, 0x397a, (state.lives - 1) & 0xff);
  renderScoreBcd(screen, state.score, 0x3918); // render_score_row2 (0x49AF)
  // Once the record falls, 0x38B8 belongs to `score_display_update`, which
  // blinks the *live score* there; leave it alone or the flash is erased.
  if ((state.recordFlags & 0x40) === 0) {
    renderScoreBcd(screen, state.topScore, 0x38b8);
  }
}
