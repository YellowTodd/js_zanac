/**
 * Airborne enemy spawning.
 *
 * Ported from:
 *   ground_struct_spawn_ctrl 0xBF2C  per-frame spawn driver (main loop, 0x4082)
 *   update_spawn_table_ptr   0xBE27  re-aim the tables from the scroll position
 *   spawn_type3d_slot        0xBF94  every 16th spawn is type 61 instead
 *   sub_bfa0                 0xBFA0  the "spawn a type-68 now" trigger
 *   alloc_entity_slot        0x4496  pool allocator (EntityPool.allocEntitySlot)
 *
 * A spawn writes **only the type byte** into the slot (0xBF79 `LD (HL),A`).
 * Position, sprite and motion all come from that type's own handler on its
 * first dispatch, exactly as the ground structures do - so an enemy type with
 * no handler ported yet occupies a slot and stays invisible.
 */

/** `spawn_table` sub-tables (kb/data/spawn_table.md). */
const TIMER_RELOAD_TABLE = 0xbe76; // 7 bytes, indexed by position >> 5
const PAIR_TABLE = 0xbe7c; // {offset, count} pairs
const ENTITY_LIST = 0xbecc; // flat type list, 0x00 terminates

/** Type spawned in place of the table entry on every 16th slot (0xBF5D). */
const TYPE_EVERY_16TH = 0x3d;
/** Type spawned by the immediate trigger at 0xBFA0. */
const TYPE_IMMEDIATE = 0x44;
/** Position clamp before indexing (0xBE35). */
const POSITION_LIMIT = 0xa0;
const POSITION_CLAMPED = 0x9f;

export class SpawnState {
  constructor() {
    /** 0xE12D control bits: 0 = recompute, 1 = stream active, 3 = blocked. */
    this.ctrl = 0;
    /** 0xE12E/0xE12F ALC spawn accumulator (high, low). */
    this.accHi = 0;
    this.accLo = 0;
    /**
     * 0xE131 - the **second** low accumulator. 0x76B0 adds the same firing
     * advance here as to 0xE12F, but its carry feeds 0xE130 through
     * `SUB_bfc8` instead of 0xE12E. Two accumulators, two counters.
     */
    this.accLo2 = 0;
    /**
     * 0xE130 the *encounter* counter - a second, slower accumulator bumped by
     * `SUB_bfc8` (0xBFC8) on kills and structure despawns, but **frozen while
     * a base is active** (0xBFCB tests 0xE150 bit 1). Its bits 4-6 pick which
     * enemy wave the type-11 spawner sends.
     */
    this.encounter = 0;
    /** 0xE132, added to accHi to form the table position. */
    this.posBias = 0;
    /** 0xE133 spawn_table_ptr. */
    this.tablePtr = ENTITY_LIST;
    /** 0xE135 sub-table counter, 0xE136 its limit. */
    this.subCtr = 0;
    this.subLimit = 0;
    /** 0xE137 spawn timer, 0xE138 its reload. */
    this.timer = 1;
    this.timerReload = 1;
    /** 0xE126 slot counter, drives the every-16th rule. */
    this.slotCtr = 0;
    /** 0xE125 bit 0: spawn one type-68 immediately. */
    this.immediate = false;
    /** 0xE142, saturating spawn counter feeding the ALC. */
    this.spawnCount = 0;
    /** 0xE124 kill countdown driving the immediate trigger (reload 0x10). */
    this.killCounter = 6; // seeded by title_screen_init (0x41F9); reloads at 0x10
    /** Types spawned this session, for verification. */
    this.spawned = [];
  }

  reset() {
    this.ctrl = 0;
    this.accHi = 0;
    this.accLo = 0;
    this.accLo2 = 0;
    this.encounter = 0;
    this.subCtr = 0;
    this.slotCtr = 0;
    this.timer = 1;
    this.spawned.length = 0;
  }
}

/**
 * `update_spawn_table_ptr` (0xBE27): re-aim the spawn tables at the current
 * position.
 *
 * The pair index is `(position >> 1) & 0x7E` - `SRL A` at 0xBE3B halves the
 * position in place before both the mask and the timer index are taken from it.
 */
export function updateSpawnTablePtr(spawn, rom) {
  spawn.ctrl &= ~0x01;

  let a = spawn.accHi + spawn.posBias;
  if (a > 0xff) a = 0xff;
  if (a >= POSITION_LIMIT) a = POSITION_CLAMPED;

  a >>= 1;
  const pairIndex = a & 0x7e;
  const timerIndex = a >> 4; // (position >> 1) >> 4 == position >> 5

  const offset = rom.byte(PAIR_TABLE + pairIndex);
  const limit = rom.byte(PAIR_TABLE + pairIndex + 1);
  // 0xBE4C: `CP (HL)` keeps the counter only while it is BELOW the limit.
  if (spawn.subCtr >= limit) spawn.subCtr = 0;
  spawn.subLimit = limit;

  spawn.timerReload = rom.byte(TIMER_RELOAD_TABLE + timerIndex);
  spawn.timer = spawn.timerReload;
  // 0xBE47 replaces E with the pair's **offset** byte, and 0xBE6B adds that
  // - not the pair index - to the entity list. Using the index walks the
  // wrong window of the list and, once the position climbs, runs straight
  // off the end into the 0x00 terminator, so nothing spawns at all.
  spawn.tablePtr = ENTITY_LIST + offset;
  spawn.listOffset = offset;
}

/**
 * `ground_struct_spawn_ctrl` (0xBF2C), run once per frame.
 * @param {import('../context.js').Context} ctx
 */
export function spawnTick(ctx) {
  const { spawn, pool, rom, state } = ctx;

  if (state.flowFlags & 0x08) return; // 0xE102 bit 3 blocks all spawning
  if (spawn.ctrl & 0x01) updateSpawnTablePtr(spawn, rom);

  if (spawn.immediate) {
    // 0xBFA0: allocate, clear the trigger, drop in a type-68.
    const slot = pool.allocEntitySlot();
    if (slot < 0) return;
    spawn.immediate = false;
    pool.slots[slot * 32] = TYPE_IMMEDIATE;
    spawn.spawned.push(TYPE_IMMEDIATE);
    return;
  }

  if (spawn.ctrl & 0x08) return; // stream blocked
  if ((spawn.ctrl & 0x02) === 0) return; // no active stream

  spawn.timer = (spawn.timer - 1) & 0xff;
  if (spawn.timer !== 0) return;
  spawn.timer = spawn.timerReload;

  const counter = spawn.slotCtr;
  spawn.slotCtr = (spawn.slotCtr + 1) & 0xff;

  if ((counter & 0x0f) === 0) {
    // 0xBF94 spawn_type3d_slot
    const slot = pool.allocEntitySlot();
    if (slot < 0) return;
    pool.slots[slot * 32] = TYPE_EVERY_16TH;
    spawn.spawned.push(TYPE_EVERY_16TH);
    return;
  }

  // 0xBF60: walk the sub-table counter, then index the flat entity list.
  const index = spawn.subCtr;
  spawn.subCtr = (spawn.subCtr + 1) & 0xff;
  if (spawn.subLimit - 1 === index) spawn.subCtr = 0;

  const type = rom.byte(spawn.tablePtr + index);
  if (type === 0) return; // 0x00 ends the list

  const slot = pool.allocEntitySlot();
  if (slot < 0) return;
  pool.slots[slot * 32] = type;
  spawn.spawned.push(type);

  // 0xBF7A: each spawn advances the ALC accumulator by 8, carrying into the
  // high byte, and bumps the saturating spawn counter at 0xE142.
  const acc = spawn.accLo + 8;
  spawn.accLo = acc & 0xff;
  if (acc > 0xff && spawn.accHi < 0xff) spawn.accHi++;
  if (spawn.spawnCount < 0xff) spawn.spawnCount++;
}
