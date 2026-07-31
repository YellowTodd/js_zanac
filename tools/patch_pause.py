"""`pause_handler` (0x4DA5): the STOP pause, with SELECT as its quiet variant."""
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


edit(
    "web/src/psg.js",
    [
        (
            "  /** `stop_all_sound` (0x516C): silence every voice and the mixer. */",
            """  /**
   * `mute_sound` (0x5208) / `restore_sound` (0x520E): the pause mute. The ROM
   * pokes 0xE200, which the driver reads as "hold every channel off". The
   * sequencer keeps running underneath, so unpausing resumes the tune
   * mid-phrase instead of restarting it.
   *
   * @param {boolean} on
   */
  setMuted(on) {
    this.muted = !!on;
  }

  /** `stop_all_sound` (0x516C): silence every voice and the mixer. */""",
        ),
    ],
)

edit(
    "web/src/sound.js",
    [
        (
            "  /** `fade_music_out` (0x5211): ramp the three music voices down. */",
            """  /** `mute_sound` (0x5208) / `restore_sound` (0x520E). */
  setMuted(on) {
    if (this.engine) this.engine.setMuted(on);
  }

  /** `fade_music_out` (0x5211): ramp the three music voices down. */""",
        ),
    ],
)

edit(
    "web/src/input.js",
    [
        (
            "export const KEY_PAUSE = 'F1';",
            """export const KEY_PAUSE = 'F1';
/**
 * Zanac reads both pause keys from MSX matrix row 7, and **SELECT modifies
 * STOP** rather than pausing on its own (0x4DB7): STOP alone gives the
 * blinking PAUSE caption, STOP+SELECT the silent hold. F2 stands in for
 * SELECT.
 */
export const KEY_SELECT = 'F2';""",
        ),
        (
            "      if (BINDINGS.has(e.code) || e.code === KEY_ESC || e.code === KEY_PAUSE) e.preventDefault();",
            "      if (\n"
            "        BINDINGS.has(e.code) ||\n"
            "        e.code === KEY_ESC ||\n"
            "        e.code === KEY_PAUSE ||\n"
            "        e.code === KEY_SELECT\n"
            "      ) {\n"
            "        e.preventDefault();\n"
            "      }",
        ),
    ],
)

p = ROOT / "web/src/game/loop.js"
t = p.read_text(encoding="utf-8")
assert "pauseHandler" not in t
t = t.rstrip() + '''

/** The caption's five name-table cells (0x396A) and its literal (0x4E40). */
const PAUSE_VRAM = 0x396a;
const PAUSE_TEXT = 'PAUSE';

/**
 * `pause_handler` (0x4DA5), run once per frame from `gameplay_frame_loop`.
 *
 * MSX matrix keys are **active low**, which flips the sense of every test
 * here: `BIT 4,A / JR Z` at 0x4DAD means "STOP *is* pressed". Bit 7 of
 * 0xE118 is a latch that keeps one press from pausing repeatedly, and bits
 * 0-4 of the same byte are the blink counter.
 *
 * **SELECT is a modifier, not a second pause key** (0x4DB7): STOP alone gives
 * the blinking PAUSE caption, STOP together with SELECT gives a silent hold
 * that leaves the display untouched.
 *
 * Getting out takes a *fresh* press: 0x4E30 only arms the exit once STOP has
 * been released, so holding the key does not immediately unpause. The PSG is
 * muted through 0x5208 rather than stopped, so the music picks up where it
 * left off.
 *
 * @param {import('../context.js').Context} ctx
 */
export function* pauseHandler(ctx) {
  const { input, screen, sound } = ctx;

  if (!input.isDown(KEY_PAUSE)) {
    ctx.pauseLatch = false; // 0x4DB1: released - re-arm
    return;
  }
  if (ctx.pauseLatch) return; // 0x4DB6: this press already handled

  const quiet = input.isDown(KEY_SELECT); // 0x4DB7
  sound.setMuted(true); // 0x5208

  // 0x4DC5: stash what the caption is about to cover.
  const saved = [];
  if (!quiet) {
    for (let i = 0; i < PAUSE_TEXT.length; i++) {
      saved.push(screen.nameTable[PAUSE_VRAM - 0x3800 + i]);
    }
  }

  let counter = 0;
  let armed = false;
  for (;;) {
    // 0x4DD5: VRAM is touched only when the low nibble wraps, and bit 4 picks
    // which of the two images to show - a 32-frame blink.
    if (!quiet && (counter & 0x0f) === 0) {
      screen.writeNameTable(PAUSE_VRAM, counter & 0x10 ? saved : PAUSE_TEXT);
    }
    yield; // 0x4E32 wait_one_frame
    counter = (counter + 1) & 0x1f; // 0x4E10

    const down = input.isDown(KEY_PAUSE);
    if (armed) {
      if (down) break; // 0x4E26: a fresh press ends it
    } else if (!down) {
      armed = true; // 0x4E30: released, so the next press counts
    }
  }

  if (!quiet) screen.writeNameTable(PAUSE_VRAM, saved); // 0x4DFC
  sound.setMuted(false); // 0x520E
  ctx.pauseLatch = true; // the exiting press must not pause again
}
'''
lines = t.splitlines(keepends=True)
last = max(i for i, l in enumerate(lines) if l.startswith("import "))
lines.insert(last + 1, "import { KEY_PAUSE, KEY_SELECT } from '../input.js';\n")
p.write_text("".join(lines), encoding="utf-8")
print("loop.js: pauseHandler added")

# flow.js: gameplay_frame_loop calls it at 0x9399, before the entity pass.
edit(
    "web/src/game/flow.js",
    [
        (
            "import { waitFrames } from './loop.js';",
            "import { waitFrames, pauseHandler } from './loop.js';",
        ),
        (
            """    baseTick(ctx);
    if (ctx.base.cleared) yield* baseClearCeremony(ctx);""",
            """    // 0x9399: the pause sits inside `gameplay_frame_loop`, so everything
            // below it - entities, spawning, collisions - simply stops.
    yield* pauseHandler(ctx);

    baseTick(ctx);
    if (ctx.base.cleared) yield* baseClearCeremony(ctx);""",
        ),
    ],
)
print("done")
