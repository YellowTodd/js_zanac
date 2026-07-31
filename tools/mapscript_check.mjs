/**
 * Walk every round's map script with the port's own operand-length table.
 *
 *   node tools/mapscript_check.mjs [--dump N]
 *
 * A wrong length desynchronises the program counter immediately, so a clean
 * walk of all nine scripts - strictly non-decreasing row triggers, every
 * command byte in range, terminating on command 9 - is the proof that the
 * interpreter consumes the stream exactly like `map_script_step` does.
 */

import { operandLength } from '../web/src/game/scroll.js';
import { loadAssets } from './lib/headless.mjs';

const STAGE_STREAM_PTR_TABLE = 0x945c;
const SCRIPT_LO = 0xa65c;
const SCRIPT_HI = 0xb7a5;
const MAX_COMMANDS = 4000;

const CMD_NAMES = [
  'spawn_ctrl',
  'placement',
  'group_set',
  'tile_copy',
  'group_add',
  'stream_slots',
  'row_param',
  'group_off',
  'round_banner',
  'round_jump',
  'glyph_blit',
  'stream_cfg',
  'spawn_pace',
];

function walk(rom, start, dumpLimit) {
  let pc = start;
  let lastRow = -1;
  const counts = new Map();
  const dump = [];
  let commands = 0;

  for (;;) {
    if (commands++ > MAX_COMMANDS) return { error: 'runaway', pc, commands };
    const row = rom.byte(pc) | (rom.byte(pc + 1) << 8);
    // 0xFFFF is the terminator: level_row_ctr never reaches it, so the script
    // simply stops firing. Round 8 uses this instead of a round_jump and runs
    // on into the ending.
    if (row === 0xffff) {
      return { ok: true, commands: commands - 1, lastRow, counts, dump, end: pc + 2 };
    }
    if (row < lastRow) return { error: `row went backwards ${lastRow} -> ${row}`, pc };
    lastRow = row;
    pc += 2;

    const byte = rom.byte(pc);
    const cmd = byte & 0x0f;
    if (cmd > 0x0c) return { error: `bad command 0x${byte.toString(16)}`, pc, row };

    let len;
    try {
      len = operandLength(rom, cmd, pc + 1);
    } catch (e) {
      return { error: e.message, pc, row };
    }
    counts.set(cmd, (counts.get(cmd) ?? 0) + 1);
    if (dump.length < dumpLimit) {
      dump.push(
        `    row ${String(row).padStart(5)}  @0x${pc.toString(16)}  ` +
          `cmd ${cmd.toString(16)} ${CMD_NAMES[cmd].padEnd(13)} +${len}`
      );
    }

    if (cmd === 0x9) {
      const target = rom.byte(pc + 1) | (rom.byte(pc + 2) << 8);
      return { ok: true, commands, lastRow, counts, dump, target, end: pc + 1 + len };
    }
    pc += 1 + len;
    if (pc < SCRIPT_LO - 0x100 || pc > SCRIPT_HI + 0x200) {
      return { error: `pc 0x${pc.toString(16)} left the script region`, row };
    }
  }
}

async function main() {
  const dumpLimit = process.argv.includes('--dump')
    ? Number(process.argv[process.argv.indexOf('--dump') + 1] ?? 10)
    : 0;
  const { rom } = await loadAssets();

  let failures = 0;
  const totals = new Map();

  for (let index = 8; index >= 0; index--) {
    const start = rom.word(STAGE_STREAM_PTR_TABLE + 2 * index);
    const round = 8 - index;
    const r = walk(rom, start, dumpLimit);
    if (r.error) {
      failures++;
      console.log(`round ${round}  0x${start.toString(16)}  FAIL: ${r.error} (pc 0x${(r.pc ?? 0).toString(16)})`);
      continue;
    }
    for (const [cmd, n] of r.counts) totals.set(cmd, (totals.get(cmd) ?? 0) + n);
    const tail = r.target === undefined ? 'ends (0xFFFF)' : `jump -> 0x${r.target.toString(16)}`;
    console.log(
      `round ${round}  0x${start.toString(16)}  ` +
        `${String(r.commands).padStart(4)} cmds  last row ${String(r.lastRow).padStart(5)}  ` +
        `end 0x${r.end.toString(16)}  ${tail}`
    );
    for (const line of r.dump) console.log(line);
  }

  console.log('\ncommand histogram:');
  for (const cmd of [...totals.keys()].sort((a, b) => a - b)) {
    console.log(`  ${cmd.toString(16)} ${CMD_NAMES[cmd].padEnd(14)} ${totals.get(cmd)}`);
  }
  console.log(failures ? `\n${failures} script(s) FAILED` : '\nall scripts walked cleanly');
  process.exitCode = failures ? 1 : 0;
}

main();
