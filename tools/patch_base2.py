"""Base system, part 2: fix signatures, wire placement, controller and dispatch."""
import pathlib

ROOT = pathlib.Path(__file__).resolve().parent.parent


def edit(rel, pairs):
    p = ROOT / rel
    t = p.read_text(encoding="utf-8")
    for old, new in pairs:
        assert old in t, f"{rel}: {old[:80]!r}"
        t = t.replace(old, new, 1)
    p.write_text(t, encoding="utf-8")
    print(f"patched {rel}")


# ---- base_segment.js: real helper signatures -------------------------------
edit(
    "web/src/game/base_segment.js",
    [
        (
            "      const dir = aimAtPlayer(ctx, s[b + 0x01], s[b + 0x02]);",
            "      const dir = aimAtPlayer(pool, rom, b);",
        ),
    ],
)

# ---- base.js: 0xE130 vs 0xE12E, and the award call -------------------------
edit(
    "web/src/game/base.js",
    [
        (
            """  if (ctx.spawn) {
    ctx.spawn.ctrl &= ~0x08; // 0x9325
    if (ctx.spawn.accHi > 0) ctx.spawn.accHi--; // dec_encounter_b (0xBFBF)
    ctx.spawn.accHi = (ctx.spawn.accHi + 0x10) & 0xff; // 0x932F: E12E += 0x10
    ctx.spawn.ctrl |= 0x01; // inc_encounter_a (0xBFAB)
  }
  void state;""",
            """  if (ctx.spawn) {
    ctx.spawn.ctrl &= ~0x08; // 0x9325
    decEncounter(ctx); // 0x9329 dec_encounter_b -> 0xE130
    ctx.spawn.accHi = (ctx.spawn.accHi + 0x10) & 0xff; // 0x932F: E12E += 0x10
    if (ctx.spawn.accHi < 0xff) ctx.spawn.accHi++; // 0x9334 inc_encounter_a
    ctx.spawn.ctrl |= 0x01;
  }
  void state;""",
        ),
        (
            """  if (ctx.spawn) {
    const acc = ctx.spawn.accHi;
    ctx.spawn.accHi = (acc - (acc >> 2)) & 0xff; // 0x90B1
    ctx.spawn.posBias = Math.max(0, ctx.spawn.posBias - 8); // 0x90BC
    if (ctx.spawn.accHi > 0) ctx.spawn.accHi--; // dec_encounter_a
    ctx.spawn.ctrl |= 0x01;
    ctx.spawn.ctrl &= ~0x08; // 0x90C5
  }""",
            """  if (ctx.spawn) {
    const acc = ctx.spawn.accHi;
    ctx.spawn.accHi = (acc - (acc >> 2)) & 0xff; // 0x90B1
    ctx.spawn.posBias = Math.max(0, ctx.spawn.posBias - 8); // 0x90BC
    if (ctx.spawn.accHi > 0) ctx.spawn.accHi--; // 0x90BF dec_encounter_a
    ctx.spawn.ctrl |= 0x01;
    // 0x90C2 SUB_bfc8 is a no-op here: 0xE150 bit 1 is still set, so the
    // encounter counter stays frozen until the flags are cleared below.
    ctx.spawn.ctrl &= ~0x08; // 0x90C5
  }""",
        ),
        (
            "  const award = rom.byte(BASE_CLEAR_AWARD_TABLE + kind);\n  ctx.addScore(award); // 0x91C1",
            "  const award = rom.byte(BASE_CLEAR_AWARD_TABLE + kind);\n  addScore(state, rom, award); // 0x91C1",
        ),
        (
            "import { ENTITY_STRIDE } from './state.js';",
            "import { ENTITY_STRIDE } from './state.js';\nimport { addScore } from './hud.js';\nimport { decEncounter } from './enemy.js';",
        ),
    ],
)

# ---- scroll.js: base placement (bit 7) and cmd 0xB parameters --------------
edit(
    "web/src/game/scroll.js",
    [
        (
            """  \\ Control-byte bits (0x95F8-0x961F): bit7 = base encounter, bit6 = wide""".replace(
                "\\", "//"
            ),
            """  // Control-byte bits (0x95F8-0x961F): bit7 = base encounter, bit6 = wide""",
        ),
        (
            """  const wide = (descriptor & 0x40) !== 0;
  const triple = (descriptor & 0x20) !== 0;
""",
            """  const wide = (descriptor & 0x40) !== 0;
  const triple = (descriptor & 0x20) !== 0;
  const isBase = (descriptor & 0x80) !== 0;
  // 0x95FC: a base batch restarts the attack list and its segment count.
  if (isBase && scroll.base) baseBatchBegin(scroll.base);
""",
        ),
        (
            """    scroll.spawnedStructures++;
  }
  return { timer, next: src };""",
            """    // 0x9626: a base batch files every placed segment in the attack list.
    if (isBase && scroll.base) baseBatchAppend(scroll.base, slot);
    scroll.spawnedStructures++;
  }
  // 0x9665: the batch end arms the encounter.
  if (isBase && scroll.base) baseBatchEnd(scroll.base);
  return { timer, next: src };""",
        ),
        (
            """    case 0xb: // 0x9742 - four state bytes, then a stream-slot 0 init
      scroll.streamCfg.set(
        [rom.byte(p), rom.byte(p + 1), rom.byte(p + 2), rom.byte(p + 3)],
        0
      );
      initStreamSlot(scroll, rom, 0, 0, 0, p + 4);
      break;""",
            """    case 0xb: // 0x9742 - the base encounter's parameters, then a slot-0 init
      scroll.streamCfg.set(
        [rom.byte(p), rom.byte(p + 1), rom.byte(p + 2), rom.byte(p + 3)],
        0
      );
      if (scroll.base) baseConfigure(scroll.base, rom, p);
      initStreamSlot(scroll, rom, 0, 0, 0, p + 4);
      break;""",
        ),
    ],
)

p = ROOT / "web/src/game/scroll.js"
t = p.read_text(encoding="utf-8")
assert "import { baseBatchBegin" not in t
# put the import after the last existing import line
lines = t.splitlines(keepends=True)
last = max(i for i, l in enumerate(lines) if l.startswith("import "))
lines.insert(
    last + 1,
    "import {\n  baseBatchAppend,\n  baseBatchBegin,\n  baseBatchEnd,\n  baseConfigure,\n} from './base.js';\n",
)
t = "".join(lines)
# ScrollState needs a handle on the base state
t = t.replace(
    "    /** 0xE714 ring head (23 -> 0 -> 23). */",
    "    /** The base encounter's state, so placement records can arm it. */\n"
    "    this.base = null;\n"
    "    /** 0xE722 warp destination set by a cleared scenario-0x0F base. */\n"
    "    this.warpTarget = 0;\n"
    "    /** 0xE714 ring head (23 -> 0 -> 23). */",
    1,
)
p.write_text(t, encoding="utf-8")
print("patched web/src/game/scroll.js (imports + state)")

# ---- enemy.js: dispatch types 73-79 ---------------------------------------
edit(
    "web/src/game/enemy.js",
    [
        (
            "  if (type === 11 || type === 69) return runWaveSpawner(pool, slot, ctx);",
            "  if (type === 11 || type === 69) return runWaveSpawner(pool, slot, ctx);\n"
            "  if (BASE_SEGMENT_TYPES.has(type)) return runBaseSegment(pool, slot, ctx, type);",
        ),
    ],
)
p = ROOT / "web/src/game/enemy.js"
t = p.read_text(encoding="utf-8")
lines = t.splitlines(keepends=True)
last = max(i for i, l in enumerate(lines) if l.startswith("import "))
lines.insert(last + 1, "import { BASE_SEGMENT_TYPES } from './base.js';\n")
lines.insert(last + 2, "import { runBaseSegment } from './base_segment.js';\n")
p.write_text("".join(lines), encoding="utf-8")
print("patched web/src/game/enemy.js (imports + dispatch)")
print("done")
