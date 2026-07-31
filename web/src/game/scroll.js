/**
 * Vertical scroll engine: the map-script interpreter and the tile-row builder.
 *
 * Ported from subsystem D (kb/subsystems/D-scroll-and-tile-rendering.md), read
 * back against the assembly rather than the KB summaries:
 *
 *   scroll_velocity_ctrl  0x9480   speed ramp + sub-frame accumulator
 *   map_script_step       0x94C3   row counter, row triggers, command dispatch
 *   map_cmd_jump_table    0x94EB   13 handlers
 *   scroll_precompute     0x97E3   pick the ring row, then build it
 *   scroll_map_reader     0x9888   assemble one 32-tile row
 *   scroll_vram_write     0x9A79   ring -> name table, called from the ISR
 *
 * Geometry (derived at 0x9A5B and 0x9AA6, not from the KB): the assembly row is
 * 32 bytes at 0xEA40, of which bytes 8..31 are the visible 24 tiles; those are
 * copied into a ring of 24 rows x 24 bytes; `scroll_vram_write` emits 24 tiles
 * per name-table row. The playfield is therefore columns 0..23 and the status
 * panel owns columns 24..31.
 */

import { COLS, BANKS, BANK_BYTES } from '../screen.js';
import { ENTITY_STRIDE } from './entity.js';
import { checkColClear } from './collision.js';
import {
  baseBatchAppend,
  baseBatchBegin,
  baseBatchEnd,
  baseConfigure,
} from './base.js';

export const PLAYFIELD_COLS = 24;
export const PLAYFIELD_ROWS = 24;
/** Width of the row the map reader assembles before the visible slice. */
export const ASSEMBLY_COLS = 32;
/** Offset of the visible slice inside the assembly row (0xEA48 - 0xEA40). */
export const ASSEMBLY_MARGIN = 8;

/** Column-group slots: 4 slots of 8 bytes at 0xE2C0 (B=4 at 0x98D2). */
const GROUP_SLOTS = 4;
/** Stream (greeble) slots: 8 slots of 4 bytes at 0xE2E0 (B=8 at 0x99FB). */
const STREAM_SLOTS = 8;
/**
 * Backing size of the assembly row. The row proper is 32 bytes at 0xEA40, but
 * stream slots address it as `0xEA40 + base + delta` and routinely run past
 * the end into scratch RAM; keeping the slack here means a run that starts
 * in range is not truncated part-way.
 */
const ASSEMBLY_BYTES = 96;
/** Stream-slot flag bits in byte 0 (0x9A00 / 0x9A04). */
const STREAM_ARMING = 0x40;
/** A tile run of this length or more is the `load_stream_slots` escape (0x9A3E). */
const STREAM_ESCAPE = 0xfe;
/** A group slot parks itself once its column position reaches this (0x9931). */
const GROUP_COLUMN_LIMIT = 0x28;
/** Slot-disabled marker written to byte 0. */
const SLOT_DISABLED = 0x80;

/** Tile-block source pointers 0xE2AC..0xE2B7, indexed by the slot param byte. */
const SOURCE_PTRS = 6;

/** Per-stage tile-block tables (kb/data/tile_tables.md), 24-byte entries. */
const TILE_TABLE_PRIMARY = 0xa444; // indexed by row & 3
const TILE_TABLE_VARIANT_A = 0xa4a4; // indexed by row & 7
const TILE_TABLE_VARIANT_B = 0xa564; // indexed by row & 7
const TILE_TABLE_FIXED_A = 0xa624;
const TILE_TABLE_FIXED_B = 0xa63c;
const TILE_COLUMN_BYTES = 24;

/** Tile-ID offsets added by the param byte's bit 7 / bit 3 (0x997C / 0x9984). */
const TILE_OFFSET_LOW = 0x17;
const TILE_OFFSET_HIGH = 0x2e;

export class ScrollState {
  constructor() {
    /** 0xE700 flags: bit0 = row ready for VRAM, bit1 = secondary signal. */
    this.flags = 0;
    /** 0xE701 stage index (8 - round), selects tile-table variants. */
    this.stage = 0;
    /** 0xE702 absolute map-row counter. */
    this.levelRow = 0;
    /** 0xE704 map-script program counter. */
    this.streamPtr = 0;
    /** 0xE706 row that fires the pending command. */
    this.nextCmdRow = 0;
    /** 0xE70F..0xE713 velocity ramp. */
    this.speed = 0;
    this.speedAcc = 0;
    this.targetSpeed = 0x34;
    this.velocityTimer = 0;
    /** The base encounter's state, so placement records can arm it. */
    this.base = null;
    /** 0xE722 warp destination set by a cleared scenario-0x0F base. */
    this.warpTarget = 0;
    /**
     * The full 0xE180/0xE198 per-row blit-control tables: [start, width] per
     * row. The credits print one window per text row; the single
     * protectRow/Start/Width trio below stays for the ROUND banner.
     */
    this.protectMap = new Uint8Array(PLAYFIELD_ROWS * 2);
    /** 0xE714 ring head (23 -> 0 -> 23). */
    this.ringRow = 0;
    /** 0xE71C, copied into the per-row param at 0x98BB. */
    this.cmd6Byte = 0;
    /** 0xE720, per-round idol table pointer (map command 8). */
    this.idolTablePtr = 0;
    /** 0xE71D: the idol allocation cursor place_tile_group hands to +0x03. */
    this.idolCursor = 0;
    /** 0xE12D spawn control, written by map command 0. */
    this.spawnCtrl = 0;

    /** The command byte of the command being executed (IX+0x0F). */
    this.cmdByte = 0;
    /** Running column position / written-tile count within one row build. */
    this.rowParam = 0; // IX+0x17
    this.lastStep = 0; // IX+0x18
    this.written = 0; // IX+0x19

    /** 0xE2AC..0xE2B7 tile-block source pointers. */
    this.sourcePtr = new Uint16Array(SOURCE_PTRS);
    /** 0xE2C0 column-group slots, 8 bytes each. */
    this.groups = new Uint8Array(GROUP_SLOTS * 8);
    /** 0xE2E0 stream slots, 4 bytes each. */
    this.streams = new Uint8Array(STREAM_SLOTS * 4);
    /** 0xE155..0xE158, written by map command B. */
    this.streamCfg = new Uint8Array(4);

    /** 0xEA40 assembly row; bytes 8..31 become the visible tiles. */
    this.assembly = new Uint8Array(ASSEMBLY_BYTES);
    /** Write cursor into `assembly` (0xE71A). */
    this.cursor = 0;
    /** 0xE800 ring of finished rows. */
    this.ring = new Uint8Array(PLAYFIELD_ROWS * PLAYFIELD_COLS);

    /** Ground-structure records the greeble streams asked for. */
    this.pendingStructures = 0;
    /** How many of those actually got a pool slot. */
    this.spawnedStructures = 0;
    /** Entity pool the streams spawn structures into; set by the game loop. */
    this.pool = null;

    /**
     * Banner protection window, the 0xE180/0xE198 per-row tables consumed by
     * `scroll_vram_inner` (0x9AAB): when a row has a nonzero entry the blit
     * writes `start` columns, skips `width`, and resumes - which is what keeps
     * the " ROUND n" text on screen while the terrain scrolls beneath it.
     * `clear_title_state` (0x41CB) zeroes the tables when the countdown ends.
     */
    this.protectRow = -1;
    this.protectStart = 0;
    this.protectWidth = 0;

    /** Set when the script runs off the end; stops the interpreter. */
    this.halted = false;
  }

  reset() {
    this.flags = 0;
    this.levelRow = 0;
    this.nextCmdRow = 0;
    this.speed = 0;
    this.speedAcc = 0;
    this.velocityTimer = 0;
    this.ringRow = 0;
    this.written = 0;
    this.cursor = 0;
    this.groups.fill(SLOT_DISABLED);
    this.streams.fill(SLOT_DISABLED);
    this.assembly.fill(0);
    this.ring.fill(0);
    this.protectMap.fill(0);
    this.pendingStructures = 0;
    this.spawnedStructures = 0;
    this.halted = false;
  }
}

/**
 * `sub_9405`/`LAB_941b`: point the interpreter at a script and read its first
 * row trigger.
 */
export function mapScriptInit(scroll, rom, ptr, resetSlots = false) {
  // 0x940C zeroes 16 entries at 0xE2C0 stride 4 - that covers byte 0 (and 4)
  // of every column group AND the status byte of all eight stream slots.
  // Map command 9 deliberately enters at 0x941B and SKIPS this, so an
  // in-round script jump keeps its terrain streams running.
  if (resetSlots) {
    for (let i = 0; i < GROUP_SLOTS; i++) {
      scroll.groups[i * 8] = SLOT_DISABLED;
      scroll.groups[i * 8 + 4] = SLOT_DISABLED;
    }
    for (let i = 0; i < STREAM_SLOTS; i++) scroll.streams[i * 4] = SLOT_DISABLED;
  }
  scroll.streamPtr = ptr;
  scroll.halted = false;
  scroll.idolCursor = 0;
  loadNextTrigger(scroll, rom);
  // 0x9424: level_row_ctr is seeded to trigger - 1, so the first step lands
  // exactly on the first command instead of skipping past it.
  scroll.levelRow = (scroll.nextCmdRow - 1) & 0xffff;
  scroll.speed = 0;
  scroll.speedAcc = 0;
  scroll.flags &= ~0x01;
}

/** `LAB_97d5` (0x97D5): consume the next 2-byte row trigger. */
function loadNextTrigger(scroll, rom) {
  const p = scroll.streamPtr;
  scroll.nextCmdRow = rom.byte(p) | (rom.byte(p + 1) << 8);
  scroll.streamPtr = (p + 2) & 0xffff;
}

/**
 * `scroll_velocity_ctrl` (0x9480). Steps the speed toward its target every
 * fourth call, then adds it to an 8-bit accumulator; a carry out means one map
 * row is due this frame.
 * @returns {boolean} true when a row should be advanced
 */
export function scrollVelocityTick(scroll, frozen = false) {
  scroll.flags &= ~0x02;
  // 0x948E: while a base is armed or fighting (0xE150 bits 0-1) the ramp is
  // suspended, so whatever speed the approach left - usually 0 - is held
  // until the encounter ends. This is the stall the player sees at a base.
  const baseHold = scroll.base !== null && (scroll.base.flags & 0x03) !== 0;
  if (!frozen && !baseHold && scroll.speed !== scroll.targetSpeed) {
    scroll.velocityTimer = (scroll.velocityTimer + 1) & 0xff;
    if ((scroll.velocityTimer & 3) === 0) {
      scroll.speed += scroll.speed < scroll.targetSpeed ? 1 : -1;
      scroll.speed &= 0xff;
    }
  }
  const sum = scroll.speed + scroll.speedAcc;
  scroll.speedAcc = sum & 0xff;
  return sum > 0xff;
}

// --------------------------------------------------------------------------
// Map script
// --------------------------------------------------------------------------

/**
 * Operand lengths for the 13 map commands. Sprint 0062 proved these byte-exact
 * by walking all nine scripts without desync; `mapScriptWalk` in
 * tools/mapscript_check.mjs re-derives the same walk from this table.
 *
 * @param {import('../assets.js').DataRom} rom
 * @param {number} cmd low nibble of the command byte
 * @param {number} p address of the first operand byte
 * @returns {number} number of operand bytes consumed
 */
export function operandLength(rom, cmd, p) {
  switch (cmd) {
    case 0x0: {
      // spawn_ctrl byte; bit 2 makes it fall into the cmd-1 placement loop.
      const ctrl = rom.byte(p);
      return ctrl & 0x04 ? 1 + 1 + 3 * rom.byte(p + 1) : 1;
    }
    case 0x1:
      return 1 + 3 * rom.byte(p);
    case 0x2:
    case 0x4:
      return 1 + 5 * rom.byte(p);
    case 0x3:
      return 1 + 2 * rom.byte(p);
    case 0x5: {
      // Records are 4 bytes, or 5 when byte 0 has bit 3 set.
      let n = rom.byte(p);
      let len = 1;
      while (n-- > 0) {
        const b0 = rom.byte(p + len);
        len += b0 & 0x08 ? 5 : 4;
      }
      return len;
    }
    case 0x6:
    case 0xa:
    case 0xc:
      return 1;
    case 0x7:
      return 1 + rom.byte(p);
    case 0x8:
    case 0x9:
      return 2;
    case 0xb:
      return 7;
    default:
      throw new Error(`unknown map command 0x${cmd.toString(16)}`);
  }
}

/**
 * `map_script_step` (0x94C3): bump the row counter, then run every command
 * whose trigger row has arrived before building this row's tiles.
 *
 * @param {{scroll: ScrollState, rom: import('../assets.js').DataRom}} ctx
 * @param {(cmd: number, byte: number, p: number) => void} [onCommand]
 */
export function mapScriptStep(ctx, onCommand) {
  const { scroll, rom } = ctx;
  scroll.levelRow = (scroll.levelRow + 1) & 0xffff;

  let guard = 0;
  while (!scroll.halted && scroll.nextCmdRow === scroll.levelRow) {
    if (++guard > 256) {
      scroll.halted = true; // runaway script: stop rather than hang the frame
      break;
    }
    const p = scroll.streamPtr;
    const byte = rom.byte(p);
    scroll.cmdByte = byte;
    const cmd = byte & 0x0f;
    const operands = p + 1;
    let length;
    try {
      length = operandLength(rom, cmd, operands);
    } catch {
      scroll.halted = true;
      break;
    }
    runCommand(ctx, cmd, byte, operands);
    if (onCommand) onCommand(cmd, byte, operands);
    if (scroll.halted) break;
    // Command 9 retargets the interpreter itself; everything else falls
    // through to the next trigger (all handlers end in JP 0x97D5).
    if (cmd !== 0x9) {
      scroll.streamPtr = (operands + length) & 0xffff;
      loadNextTrigger(scroll, rom);
    }
  }

  if (!scroll.halted) scrollPrecompute(ctx);
}

/** Dispatch one map command. */
function runCommand(ctx, cmd, byte, p) {
  const { scroll, rom } = ctx;
  switch (cmd) {
    case 0x0: // 0x97A8 - spawn control, optionally falling into placement
      scroll.spawnCtrl = rom.byte(p);
      if (ctx.spawn) ctx.spawn.ctrl = scroll.spawnCtrl;
      // 0x97AD: bit 2 makes the command fall straight into the cmd-1 body,
      // with the wave records following the control byte.
      if (scroll.spawnCtrl & 0x04) placeWaves(scroll, rom, p + 1);
      break;
    case 0x1: // 0x97B3 - scripted enemy waves
      placeWaves(scroll, rom, p);
      break;
    case 0x3: // 0x9537 - relocate column-group slots
      moveGroups(scroll, rom, p);
      break;
    case 0xa: // 0x96E5 - repaint the rubble tile colours
      recolourTiles(ctx, rom.byte(p));
      break;
    case 0x2: // 0x9505 - configure column-group slots
      configureGroups(scroll, rom, p, false);
      break;
    case 0x4: // 0x956C - same, but additive on the column position
      configureGroups(scroll, rom, p, true);
      break;
    case 0x5: // 0x95A0 - activate greeble stream slots
      loadStreamSlots(scroll, rom, p, 0);
      break;
    case 0x6: // 0x9678 - per-row param seed
      scroll.cmd6Byte = rom.byte(p);
      break;
    case 0xb: // 0x9742 - the base encounter's parameters, then a slot-0 init
      scroll.streamCfg.set(
        [rom.byte(p), rom.byte(p + 1), rom.byte(p + 2), rom.byte(p + 3)],
        0
      );
      if (scroll.base) baseConfigure(scroll.base, rom, p);
      initStreamSlot(scroll, rom, 0, 0, 0, p + 4);
      break;
    case 0x7: // 0x9680 - disable the listed slots
      {
        const n = rom.byte(p);
        for (let i = 0; i < n; i++) {
          const slot = rom.byte(p + 1 + i) & (GROUP_SLOTS - 1);
          scroll.groups[slot * 8] = SLOT_DISABLED;
        }
      }
      break;
    case 0x8: // 0x9699 - "ROUND n" banner + per-round idol table pointer
      scroll.idolTablePtr = rom.byte(p) | (rom.byte(p + 1) << 8);
      if (ctx.onRoundBanner) ctx.onRoundBanner();
      break;
    case 0x9: // 0x96DE - jump to another round's script
      {
        const target = rom.byte(p) | (rom.byte(p + 1) << 8);
        if (ctx.onRoundJump) ctx.onRoundJump(target);
        else scroll.halted = true;
      }
      break;
    case 0xc: // 0x977D - scripted ALC spawn-pace nudge
      if (ctx.onSpawnPace) ctx.onSpawnPace(rom.sbyte(p));
      break;
    default:
      break;
  }
}

/**
 * Command 1 (0x97B3), also reached from command 0 when its control byte has
 * bit 2 set: **scripted enemy waves**.
 *
 * Each record is three bytes and becomes one entity of type 0x45 (69), the
 * invisible wave emitter `base_spawner_active`. The three bytes land in the
 * slot's +0x01/+0x02/+0x03, which that handler immediately re-reads as
 * **(enemy type, count, fire interval)** before `random_x_pos` overwrites the
 * position - the same shape as the type-11 spawner's table, but written
 * inline in the script instead of chosen by the encounter counter.
 *
 * A blocked column consumes its three bytes and places nothing (0x97C4).
 */
function placeWaves(scroll, rom, p) {
  const count = rom.byte(p);
  let src = (p + 1) & 0xffff;
  for (let i = 0; i < count; i++) {
    placeWaveRecord(scroll.pool, rom, src);
    src = (src + 3) & 0xffff;
  }
}

/**
 * `sub_97BC` — one wave record. Shared by map command 1 and, less obviously,
 * by `fire_select` when the player takes **fire weapon 2** (0x7591).
 *
 * @param {import('./entity.js').EntityPool|null} pool
 * @param {number} p address of the 3-byte `[enemy type][count][interval]`
 */
export function placeWaveRecord(pool, rom, p) {
  if (!pool) return;
  const { slot, blocked } = checkColClear(pool);
  if (blocked || slot < 0) return;
  const b = slot * ENTITY_STRIDE;
  pool.clear(slot);
  pool.slots[b] = 0x45;
  pool.slots[b + 0x01] = rom.byte(p);
  pool.slots[b + 0x02] = rom.byte((p + 1) & 0xffff);
  pool.slots[b + 0x03] = rom.byte((p + 2) & 0xffff);
}

/**
 * Command 3 (0x9537): **move a column-group slot**. Each 2-byte record is
 * `[src][dst]`; the eight descriptor bytes are copied from src to dst and the
 * source is then disabled (0x9552 writes 0x80 over its status byte), so a
 * running greeble stream changes which column it feeds without restarting.
 *
 * The operand order is easy to get backwards: 0x953F builds `DE` from the
 * **first** byte and 0x954D builds `HL` from the second, then `EX DE,HL`
 * (0x954F) swaps them, so the `LD A,(HL) / LD (DE),A` pair that follows reads
 * the first slot and writes the second.
 */
function moveGroups(scroll, rom, p) {
  const count = rom.byte(p);
  for (let i = 0; i < count; i++) {
    const src = (rom.byte(p + 1 + i * 2) & (GROUP_SLOTS - 1)) * 8;
    const dst = (rom.byte(p + 2 + i * 2) & (GROUP_SLOTS - 1)) * 8;
    for (let k = 0; k < 8; k++) scroll.groups[dst + k] = scroll.groups[src + k];
    scroll.groups[src] = SLOT_DISABLED; // 0x9552
  }
}

/** `glyph_col_data` (0x973E): high nibbles for tiles 0xA7-0xAA. */
const GLYPH_COL_DATA = [0x00, 0x00, 0x70, 0x50];

/**
 * Command A (0x96E5): **repaint the debris tiles for the current terrain**.
 *
 * The operand is a colour byte. Tiles 0x3A-0x3E - the crater/rubble set the
 * structure stamper leaves behind - take it verbatim; tiles 0xA7-0xAA take
 * `glyph_col_data[i] | (fill & 0x0F)`. Both writes cover all eight rows of
 * each tile and all three Screen-2 banks (0x9732 adds 0x800 per pass), which
 * is why wreckage always matches the ground it is lying on.
 */
function recolourTiles(ctx, fill) {
  const screen = ctx.screen;
  if (!screen) return;
  const paint = (tile, value) => {
    for (let bank = 0; bank < BANKS; bank++) {
      const at = bank * BANK_BYTES + tile * 8;
      for (let row = 0; row < 8; row++) screen.colors[at + row] = value;
    }
  };
  for (let i = 0; i < 5; i++) paint(0x3a + i, fill); // 0x21D0, C = 5
  for (let i = 0; i < 4; i++) paint(0xa7 + i, GLYPH_COL_DATA[i] | (fill & 0x0f));
}

/**
 * Commands 2 and 4 (0x9505 / 0x956C): N records of 5 bytes into the
 * column-group slots at 0xE2C0. Command 4 adds to the existing column
 * position instead of replacing it.
 */
function configureGroups(scroll, rom, p, additive) {
  const n = rom.byte(p);
  let src = p + 1;
  for (let i = 0; i < n; i++) {
    const slot = rom.byte(src) & (GROUP_SLOTS - 1);
    const base = slot * 8;
    const status = rom.byte(src + 1);
    scroll.groups[base] = additive ? (scroll.groups[base] + status) & 0xff : status;
    scroll.groups[base + 1] = rom.byte(src + 2);
    const ptr = rom.byte(src + 3) | (rom.byte(src + 4) << 8);
    scroll.groups[base + 2] = ptr & 0xff;
    scroll.groups[base + 3] = ptr >> 8;
    scroll.groups[base + 6] = 1; // timers forced to 1 on load
    scroll.groups[base + 7] = 1;
    src += 5;
  }
}

// --------------------------------------------------------------------------
// Greeble stream slots
// --------------------------------------------------------------------------

/**
 * `load_stream_slots` (0x95A8): `[N]` followed by N slot records.
 *
 * Record: `[b0][colBase]([timer])[lo][hi]` - four bytes, or five when b0 has
 * bit 3 set. b0's low bits pick the slot; bit 3 also means "start armed", so
 * the slot idles for `timer` rows before it begins emitting.
 *
 * @param {number} colBase added to every record's column base (C at 0x95C1)
 */
function loadStreamSlots(scroll, rom, p, colBase) {
  let n = rom.byte(p);
  let src = p + 1;
  while (n-- > 0) {
    const b0 = rom.byte(src);
    const slot = (b0 & ~0x08 & 0xff) % STREAM_SLOTS;
    src = initStreamSlot(scroll, rom, slot, b0, colBase, src + 1);
  }
  return src; // the address just past the consumed records (HL on return)
}

/**
 * `init_stream_slot` (0x95C0). `p` addresses the record's column-base byte.
 * @returns {number} the address just past the record
 */
function initStreamSlot(scroll, rom, slot, b0, colBase, p) {
  const s = slot * 4;
  scroll.streams[s] = (rom.byte(p) + colBase) & 0xff;
  let src = p;
  if (b0 & 0x08) {
    scroll.streams[s] |= STREAM_ARMING;
    src += 1;
    scroll.streams[s + 1] = rom.byte(src);
  }
  src += 1;
  let cursor = rom.byte(src) | (rom.byte(src + 1) << 8);
  src += 2;

  if ((scroll.streams[s] & STREAM_ARMING) === 0) {
    // Not armed: take the first timer straight away, and let a 0 marker run
    // the ground-structure placement before it.
    let timer = rom.byte(cursor);
    cursor = (cursor + 1) & 0xffff;
    if (timer === 0) {
      const group = placeTileGroup(scroll, rom, cursor, scroll.streams[s] & 0x3f);
      timer = group.timer;
      cursor = group.next;
    }
    scroll.streams[s + 1] = timer;
  }
  scroll.streams[s + 2] = cursor & 0xff;
  scroll.streams[s + 3] = cursor >> 8;
  return src;
}

/**
 * `place_tile_group` (0x95ED): a ground-structure batch embedded in a greeble
 * stream. The descriptor's low five bits are the record count; every record
 * costs three stream bytes whether the column was clear (placed at 0x963A) or
 * blocked (skipped by the three `INC DE`s at 0x960C).
 *
 * Record: `[type][y][xCell]`, with the entity's X computed as
 * `column * 8 + xCell - 0x20` (0x9645) - the 0x20 undoes the sprite attribute
 * table's early-clock bias.
 *
 * @param {number} column the owning stream slot's column base (IY+0)
 * @returns {{timer: number, next: number}}
 */
export function placeTileGroup(scroll, rom, p, column = 0) {
  const timer = rom.byte(p);
  const descriptor = rom.byte((p + 1) & 0xffff);
  const records = descriptor & 0x1f;
  let src = (p + 2) & 0xffff;

  // Control-byte bits (0x95F8-0x961F): bit7 = base encounter, bit6 = wide
  // structure (consumes one idol-cursor slot into +0x03), bit5 = triple width
  // (consumes one more). The cursor (0xE71D) advances on the BLOCKED path too
  // (0x9614), so later structures keep their idol-table alignment.
  const wide = (descriptor & 0x40) !== 0;
  const triple = (descriptor & 0x20) !== 0;
  const isBase = (descriptor & 0x80) !== 0;
  // 0x95FC: a base batch restarts the attack list and its segment count.
  if (isBase && scroll.base) baseBatchBegin(scroll.base);

  for (let i = 0; i < records; i++) {
    const type = rom.byte(src);
    const y = rom.byte((src + 1) & 0xffff);
    const xCell = rom.byte((src + 2) & 0xffff);
    src = (src + 3) & 0xffff;

    scroll.pendingStructures++;
    if (!scroll.pool) continue;
    const { slot, blocked } = checkColClear(scroll.pool);
    if (blocked || slot < 0) {
      if (wide) scroll.idolCursor = (scroll.idolCursor + 1) & 0xff;
      if (wide && triple) scroll.idolCursor = (scroll.idolCursor + 1) & 0xff;
      continue;
    }

    const b = slot * ENTITY_STRIDE;
    scroll.pool.clear(slot);
    scroll.pool.slots[b] = type;
    scroll.pool.slots[b + 0x01] = y;
    scroll.pool.slots[b + 0x02] = (column * 8 + xCell - 0x20) & 0xff;
    if (wide) {
      // 0x9653: slot +0x03 = the global idol cursor, then cursor++
      scroll.pool.slots[b + 0x03] = scroll.idolCursor;
      scroll.idolCursor = (scroll.idolCursor + 1) & 0xff;
      if (triple) scroll.idolCursor = (scroll.idolCursor + 1) & 0xff;
    }
    // 0x9626: a base batch files every placed segment in the attack list.
    if (isBase && scroll.base) baseBatchAppend(scroll.base, slot);
    scroll.spawnedStructures++;
  }
  // 0x9665: the batch end arms the encounter.
  if (isBase && scroll.base) baseBatchEnd(scroll.base);
  return { timer, next: src };
}

/**
 * Stream-slot pass at 0x99F7-0x9A5A: each active slot splices one run of tiles
 * into the assembly row per map row.
 *
 * Stream grammar, from the slot cursor: `[delta][len][len tiles]`, where the
 * run is written at `base + delta` within the row. `len == 0` emits nothing;
 * `len >= 0xFE` is an escape that loads more slots instead.
 */
function runStreamSlots(scroll, rom) {
  for (let slot = 0; slot < STREAM_SLOTS; slot++) {
    const s = slot * 4;
    let flags = scroll.streams[s];
    if (flags === SLOT_DISABLED) continue;

    let cursor = scroll.streams[s + 2] | (scroll.streams[s + 3] << 8);

    if (flags & STREAM_ARMING) {
      scroll.streams[s + 1] = (scroll.streams[s + 1] - 1) & 0xff;
      if (scroll.streams[s + 1] !== 0) continue; // still idling
      let timer = rom.byte(cursor);
      cursor = (cursor + 1) & 0xffff;
      if (timer === 0) {
        const group = placeTileGroup(scroll, rom, cursor, flags & 0x3f);
        timer = group.timer;
        cursor = group.next;
      }
      scroll.streams[s + 1] = timer;
      flags &= ~STREAM_ARMING;
      scroll.streams[s] = flags;
    }

    const at = (flags + rom.byte(cursor)) & 0xff;
    cursor = (cursor + 1) & 0xffff;
    const len = rom.byte(cursor);
    cursor = (cursor + 1) & 0xffff;

    if (len >= STREAM_ESCAPE) {
      // 0x9A68: the run length doubles as "load more slots from here".
      //
      // The branch back at 0x9A74 tests the flags `CP 0xFE` left at 0x9A3E,
      // saved across the call by PUSH/POP AF - so **0xFE** (Z set) skips the
      // bookkeeping below and 0xFF (Z clear) performs it. Skipping matters:
      // load_stream_slots may have just reinitialised this very slot, and
      // writing the stale local cursor and timer back over it corrupts the
      // fresh configuration, leaving the slot emitting the same run on every
      // row forever - a stuck vertical stripe down the playfield.
      //
      // On the 0xFF path the cursor written back is HL AS load_stream_slots
      // LEFT IT (0x9A44 stores the advanced pointer) - i.e. past the consumed
      // slot records. Storing the pre-call cursor instead makes the next row
      // reparse those records as [delta][len][tiles], spraying garbage tiles
      // (ASCII-range bytes) across the playfield.
      const end = loadStreamSlots(scroll, rom, cursor, flags);
      if (len === STREAM_ESCAPE) continue;
      cursor = end;
    } else if (len !== 0) {
      for (let i = 0; i < len; i++) {
        const dst = at + i;
        if (dst < ASSEMBLY_BYTES) scroll.assembly[dst] = rom.byte(cursor);
        cursor = (cursor + 1) & 0xffff;
      }
    }

    scroll.streams[s + 2] = cursor & 0xff;
    scroll.streams[s + 3] = cursor >> 8;
    scroll.streams[s + 1] = (scroll.streams[s + 1] - 1) & 0xff;
    if (scroll.streams[s + 1] === 0) scroll.streams[s] = SLOT_DISABLED;
  }
}

// --------------------------------------------------------------------------
// Row building
// --------------------------------------------------------------------------

/**
 * `scroll_precompute` (0x97E3): step the ring head backwards (new rows enter
 * at the top), build the row, then raise the DMA-ready flag.
 */
function scrollPrecompute(ctx) {
  const { scroll } = ctx;
  scroll.ringRow = scroll.ringRow === 0 ? PLAYFIELD_ROWS - 1 : scroll.ringRow - 1;
  scroll.flags &= ~0x01;
  scrollMapReader(ctx);
  scroll.flags |= 0x03;
}

/** Refresh the stage-indexed tile-block pointers (0x9888-0x98BA). */
function updateSourcePointers(scroll) {
  const row = scroll.levelRow & 0xff;
  scroll.sourcePtr[1] = TILE_TABLE_PRIMARY + TILE_COLUMN_BYTES * (row & 3);
  scroll.sourcePtr[2] = TILE_TABLE_VARIANT_A + TILE_COLUMN_BYTES * (row & 7);
  scroll.sourcePtr[3] = TILE_TABLE_VARIANT_B + TILE_COLUMN_BYTES * (row & 7);
  scroll.sourcePtr[4] = TILE_TABLE_FIXED_A;
  scroll.sourcePtr[5] = TILE_TABLE_FIXED_B;
  if (scroll.sourcePtr[0] === 0) scroll.sourcePtr[0] = TILE_TABLE_PRIMARY;
}

/**
 * `scroll_map_reader` (0x9888): assemble one 32-tile row from the active
 * column-group slots, pad the tail from a tile-block table, then copy the
 * visible 24 tiles into the ring.
 */
export function scrollMapReader(ctx) {
  const { scroll, rom } = ctx;
  updateSourcePointers(scroll);

  scroll.rowParam = scroll.cmd6Byte;
  scroll.lastStep = 0;
  scroll.written = 0;
  scroll.cursor = 0;
  scroll.assembly.fill(0);

  for (let slot = 0; slot < GROUP_SLOTS; slot++) {
    const g = slot * 8;
    if (scroll.groups[g] === SLOT_DISABLED) continue;
    advanceGroup(scroll, rom, g);
    emitGroup(scroll, rom, g);
  }

  // 0x99D2: pad whatever is left of the 32-tile row from a tile-block column.
  if (scroll.written < ASSEMBLY_COLS) {
    const src = scroll.sourcePtr[scroll.rowParam & 7] + scroll.written;
    let dst = scroll.cursor;
    for (let i = scroll.written; i < ASSEMBLY_COLS && dst < ASSEMBLY_COLS; i++) {
      scroll.assembly[dst++] = rom.byte(src + (i - scroll.written));
    }
    scroll.cursor = dst;
  }

  runStreamSlots(scroll, rom);

  // 0x9A5B: the visible slice becomes this ring row.
  const ringBase = scroll.ringRow * PLAYFIELD_COLS;
  for (let i = 0; i < PLAYFIELD_COLS; i++) {
    scroll.ring[ringBase + i] = scroll.assembly[ASSEMBLY_MARGIN + i];
  }
}

/**
 * Slot bookkeeping at 0x98DD-0x9929: run down the per-column timers and, when
 * they expire, walk the column-descriptor records.
 *
 * Descriptor grammar, read at 0x98F6/0x9901:
 *   [cnt][b0][lo][hi]  b0 = 0x00 -> LINK: continue the stream at 0xHILO
 *                      b0 = 0xFF -> ADVANCE: column += cnt, record is 2 bytes
 *                      else      -> COLUMN: tile source = 0xHILO
 */
function advanceGroup(scroll, rom, g) {
  scroll.groups[g + 6] = (scroll.groups[g + 6] - 1) & 0xff;
  if (scroll.groups[g + 6] !== 0) return;

  let hl;
  if (scroll.groups[g + 7] === 0) {
    hl = scroll.groups[g + 2] | (scroll.groups[g + 3] << 8);
    readDescriptor(scroll, rom, g, hl);
    return;
  }
  scroll.groups[g + 7] = (scroll.groups[g + 7] - 1) & 0xff;
  if (scroll.groups[g + 7] !== 0) {
    hl = scroll.groups[g + 2] | (scroll.groups[g + 3] << 8);
    readDescriptor(scroll, rom, g, hl);
    return;
  }
  hl = ((scroll.groups[g + 2] | (scroll.groups[g + 3] << 8)) + 3) & 0xffff;
  readCount(scroll, rom, g, hl);
}

/** 0x98F6: take the run count, then fall into the descriptor body. */
function readCount(scroll, rom, g, hl) {
  let guard = 0;
  for (;;) {
    if (++guard > 64) return; // malformed link chain
    scroll.groups[g + 7] = rom.byte(hl);
    hl = (hl + 1) & 0xffff;
    scroll.groups[g + 2] = hl & 0xff;
    scroll.groups[g + 3] = hl >> 8;
    const next = readDescriptor(scroll, rom, g, hl);
    if (next === null) return;
    hl = next;
  }
}

/**
 * 0x9901: read `[b0][lo][hi]`. Returns the address to restart `readCount` at
 * for LINK/ADVANCE, or null when a tile source was selected.
 * @returns {number|null}
 */
function readDescriptor(scroll, rom, g, hl) {
  const b0 = rom.byte(hl);
  scroll.groups[g + 6] = b0;
  const loAddr = (hl + 1) & 0xffff;
  const hiAddr = (hl + 2) & 0xffff;
  const ptr = rom.byte(loAddr) | (rom.byte(hiAddr) << 8);

  if (b0 === 0x00) return ptr; // LINK
  if (b0 === 0xff) {
    // ADVANCE: the record is only [cnt][FF]; the next one starts at `loAddr`.
    scroll.groups[g] = (scroll.groups[g] + scroll.groups[g + 7]) & 0xff;
    return loAddr;
  }
  scroll.groups[g + 4] = ptr & 0xff; // COLUMN
  scroll.groups[g + 5] = ptr >> 8;
  return null;
}

/**
 * 0x992E-0x99B2: place this slot's tile-source record into the assembly row.
 *
 * Tile-source record: `[step][len][len tiles]`. `step` advances the slot's
 * column position; the tiles are copied verbatim, or biased by +0x17 / +0x2E
 * when the param byte's bit 7 (and bit 3) are set.
 */
function emitGroup(scroll, rom, g) {
  const column = scroll.groups[g];
  if (column >= GROUP_COLUMN_LIMIT) {
    scroll.groups[g] = SLOT_DISABLED;
    return;
  }

  if (scroll.written < column) {
    // Fill the gap up to this slot's column from a tile-block table.
    const param = scroll.groups[g + 1];
    const src = scroll.sourcePtr[(param >> 4) & 7] + scroll.written;
    for (let i = 0; i < column - scroll.written && scroll.cursor < ASSEMBLY_COLS; i++) {
      scroll.assembly[scroll.cursor++] = rom.byte(src + i);
    }
  } else {
    // Already past it: rewind the cursor so the record overwrites.
    scroll.cursor = Math.max(0, scroll.cursor - (scroll.written - column));
  }

  scroll.lastStep = column;
  let hl = scroll.groups[g + 4] | (scroll.groups[g + 5] << 8);
  const step = rom.byte(hl);
  const len = rom.byte((hl + 1) & 0xffff);
  hl = (hl + 2) & 0xffff;

  if (len !== 0) {
    const param = scroll.groups[g + 1];
    const bias = param & 0x80 ? (param & 0x08 ? TILE_OFFSET_HIGH : TILE_OFFSET_LOW) : 0;
    for (let i = 0; i < len; i++) {
      if (scroll.cursor < ASSEMBLY_COLS) {
        scroll.assembly[scroll.cursor++] = (rom.byte(hl) + bias) & 0xff;
      }
      hl = (hl + 1) & 0xffff;
    }
  }

  scroll.written = (column + len) & 0xff;
  scroll.groups[g + 4] = hl & 0xff;
  scroll.groups[g + 5] = hl >> 8;
  scroll.groups[g] = (scroll.groups[g] + step) & 0xff;
  // 0x99AC: the row's pad param is **the last slot that emitted**, not the
  // map-command byte it started as. A slot that ran off the row (0x99C4) never
  // gets here, so it cannot claim the tail.
  scroll.rowParam = scroll.groups[g + 1];
}

/**
 * `scroll_vram_write` (0x9A79): blit the ring into the name table, starting at
 * the ring head and wrapping, 24 tiles per row.
 * @param {import('../screen.js').Screen} screen
 * @param {ScrollState} scroll
 */
export function scrollVramWrite(screen, scroll) {
  if ((scroll.flags & 0x01) === 0) return;
  scroll.flags &= ~0x01;
  for (let row = 0; row < PLAYFIELD_ROWS; row++) {
    const src = ((scroll.ringRow + row) % PLAYFIELD_ROWS) * PLAYFIELD_COLS;
    const dst = row * COLS;
    let pStart = -1;
    let pWidth = 0;
    if (row === scroll.protectRow) {
      pStart = scroll.protectStart;
      pWidth = scroll.protectWidth;
    } else if (scroll.protectMap[row * 2 + 1] !== 0) {
      pStart = scroll.protectMap[row * 2];
      pWidth = scroll.protectMap[row * 2 + 1];
    }
    for (let col = 0; col < PLAYFIELD_COLS; col++) {
      if (col >= pStart && col < pStart + pWidth) {
        continue; // 0x9AC5: the protected window is skipped, not repainted
      }
      screen.nameTable[dst + col] = scroll.ring[src + col];
    }
  }
}
