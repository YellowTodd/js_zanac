---
id: "0033"
status: done
range: 0x91A6-0x92D0,0x9315-0x93E7,0x946E-0x946E,0x986E-0x986E,0x9AA6-0x9AA6
strategy: forward_from_caller
budget_turns: 30
---

# Sprint 0033 — Credits setup: full initialization for `scripts/credits.tcl`

## Goal

The current `scripts/credits.tcl` only sets `E102` bit 3, which starts the
credits display loop but skips the full setup block at `LAB_91fd` (0x91FD).
The result is:

- **No ending music** (sound event 0x0C not fired)
- **Enemies still fire** (PSG/enemy state not reset)
- **Logo graphics garbled** (sprite pattern table not loaded from level data at 0xBBB4)

Identify every initialization step in `LAB_91fd` → `LAB_92af`, understand what
each one does, and produce a working `credits.tcl` that replicates them from TCL.

## Inputs

- `kb/guides/input-state-machine.md` — end-credits display loop (LAB_46d9)
- `kb/guides/keyboard-input.md` — E100 / E147 state
- `kb/data/scroll_state.md` — E700, E710, E712, IX scroll pointer
- Source lines 6246–6340 (`LAB_91fd` → `LAB_92af` → `sub_92ca`)
- Source lines 6183–6245 (context before `LAB_91fd`)

## Setup block: `LAB_91fd` (0x91FD) — annotated

```
CALL sub_516c            ; 1. reset PSG + enemy state (stops firing)
CALL sub_42ed            ; 2. VDP interrupt toggle
LD HL, 0xE800            ; 3. VRAM 0x3C00 ← RAM 0xE800 (0x240 bytes)?
LD DE, 0x3C00            ;    Clear/copy sprite pattern table
LD BC, 0x240
CALL 0x005C              ;    FILVRM or LDIRVM (TBD)
LD HL, 0xBBB4            ; 4. advance level stream to 0xBBB4
CALL sub_9433            ;    (loads credits sprite patterns into VRAM)
CALL sub_946e            ; 5. additional level processing
LD HL, 0xE800            ; 6. RAM copy: E800-EA3F → EB00-ED3F
LD DE, 0xEB00
LD BC, 0x240
LDIR
LD HL, 0x3C00            ; 7. VRAM write: 0x3C00 ← 0xE800 (0x240 bytes)
LD DE, 0xE800
LD BC, 0x240
CALL 0x0059              ;    SETWRT / LDIRVM (TBD)
LD (IX+0x57), 0xD1       ; 8. scroll engine: IX+0x57 = 0xD1 (mode flags)
LD (IX+0x56), 0x0C       ;    IX+0x56 = 0x0C
LD (IX+0x50), 0x01       ;    IX+0x50 = 0x01
LD (E700),    0x0C       ; 9. E700 = 0x0C (scroll engine mode: bits 2+3 set)
LD (E710),    0x20       ; 10. E710 = 0x20 (scroll speed / offset)
LD A, 0x0C
CALL sub_5189            ; 11. play_sound_event(0x0C) — ending music
JP sub_92ca              ; → RES E102 bit 2, RET
```

Then `LAB_92af` (0x92AF):
```
LD (E722), 0xA6F4        ; level stream pointer for credits
SET E102 bit 5           ; level_complete (cleared by LAB_40da on same frame)
SET E102 bit 3           ; end_credits  → LAB_46d5 on next frame
LD B, 0x3C
CALL sub_9393            ; run 60 transition frames
LD (E700), 0x00          ; scroll engine back to default mode
LD (E712), 0x80
; falls through to sub_92ca → RES E102 bit 2, RET
```

## Key questions to answer

1. **0x005C (BIOS)**: is this FILVRM (fill VRAM with constant) or LDIRVM (block
   copy RAM→VRAM)?  Parameters: HL=0xE800, DE=0x3C00, BC=0x240.  If FILVRM,
   what byte fills VRAM?  If LDIRVM, what is in RAM 0xE800 at this point?

2. **sub_9433(HL=0xBBB4)**: what does this do to VRAM and game state?  Does it
   directly write sprite pattern data to VRAM 0x0000 or 0x3C00?  The KB says
   sub_9433 stores a level pointer to E704 and calls sub_940c (level streaming
   init).  Does the 0xBBB4 level data contain sprite pattern blitting commands?

3. **sub_946e**: what does this do?  Called right after sub_9433.

4. **E700 = 0x0C**: E700 bits 2+3 — what do they control in the scroll engine?
   Why are they set here (and cleared to 0 again inside LAB_92af)?

5. **E710 = 0x20**: what does E710 control?  Sprint 0029 says E710 is related to
   level row counter or scroll speed — confirm.

6. **sub_516c**: confirm it stops enemies from firing (not just resets PSG).
   What flag or state prevents new enemy shots after this call?

7. **0x0059 (BIOS) + second block**: HL=0x3C00, DE=0xE800 — which direction
   is this copy?  VRAM←RAM or RAM←VRAM?

8. **IX scroll pointer**: IX points to the scroll engine state block (E700
   area?).  Where is IX loaded before this code?  `(IX+0x57)`, `(IX+0x56)`,
   `(IX+0x50)` — what are these fields?

## Verification plan

### Step 1 — Capture state at LAB_92af (live, breakpoint)

Break at 0x92AF at the exact moment the game normally triggers credits
(use `scripts/warp.tcl` to reach round 8 quickly, then wait for end boss).
Dump the complete state needed to replicate the setup:

```python
with ZanacGame.launch() as game:
    msx = game.client
    game.wait_for_title(); game.start_game()
    # warp to round 8 (final area)
    msx.cmd("source scripts/warp.tcl")
    msx.cmd("warp 8")

    msx.cmd("set ::hit92af 0")
    bp = msx.set_breakpoint(0x92AF, "set ::hit92af 1; debug break")
    msx.cont()
    msx.poll_flag("hit92af", interval=1.0, timeout=300.0)
    msx.remove_breakpoint(bp)

    # Dump key state
    ix = int(msx.cmd("reg ix"), 16)
    print(f"IX = 0x{ix:04X}")
    for off in [0x50, 0x56, 0x57]:
        v = msx.read_byte(ix + off)
        print(f"  (IX+0x{off:02X}) = 0x{v:02X}")
    for addr in [0xE700, 0xE710, 0xE712, 0xE722, 0xE102]:
        v = msx.read_byte(addr)
        print(f"  E{addr-0xE000:03X} = 0x{v:02X}")
    # Check VRAM 0x3C00 (first 32 bytes of sprite patterns)
    vram = bytes(msx.read_memory(0x3C00, 32))
    print("VRAM 0x3C00:", vram.hex())
```

### Step 2 — Capture state just BEFORE and AFTER sub_9433(0xBBB4)

Break at the CALL 0x9433 in LAB_91fd, dump VRAM 0x3C00 before and after to
confirm it loads sprite patterns.

### Step 3 — Identify sub_946e

Read source for sub_946e (address 0x946E).  Confirm whether it blits more
data to VRAM or just updates RAM state.

### Step 4 — Decode E700 = 0x0C scroll behavior (static)

Read source for sub_9480 (scroll engine, called from main loop) around the
bit tests on E700.  Find what bits 2+3 change.

### Step 5 — Produce working credits.tcl

With the above answers, write `scripts/credits.tcl` that replicates the full
`LAB_91fd` setup from TCL without needing to run through the game:

- Call play_sound_event(0x0C) by writing directly to the sound-engine channel
  slots at 0xE20C (format from sprint 0020 sound engine).
- Call sub_516c by using a `debug run` or breakpoint trampoline.
- Set all identified RAM/IX variables directly.
- Set E102 bit 3 to arm the credits display.

## Additional KB entries required (open-ref cleanup)

Two scroll-engine sub-routines called by already-documented symbols have no KB
entries.  Add as symbol files during this sprint (static-only):

| Address | Caller | Purpose (hypothesis) |
|---------|--------|----------------------|
| 0x986E | `scroll_map_reader` | Column-tile copier: transposes 24-row tile column from map buffer (HL+BC) into E800 buffer (DE+BC), 24 iterations |
| 0x9AA6 | `scroll_vram_write` | Inner VRAM write sub-loop — sequential byte stream to VDP port |

## Summary (filled at end)

**Outcome:** `scripts/credits.tcl` now triggers the real ending from any active
gameplay state — verified by PNG screenshot against `savestates/game-end.oms`
(fade to black, fast round-0 terrain scroll, controllable player ship, ending
music, flashing developer names, clean ZANAC logo). User-confirmed working.

### The fix
The old script set only `E102` bit 3, so `load_logo_tiles` never ran and the
logo rendered as a garbled multicolour block. The working trigger reproduces
**`LAB_92af`** and additionally forces `E701 = 0`:

| Write | Why |
|-------|-----|
| `E701 = 0x00` | the logo loader (`load_logo_tiles`, 0x5C3C, via `LAB_412a`) runs only when **both** old (E701) and new (from E722) stage are multiples of 8; the real ending satisfies this by transitioning round 8 → 0 |
| `E722 = 0xA6F4` | ending stream pointer (round 0); read by `LAB_40da` at 0x40DD |
| `E712 = 0x80` | fast "game-beaten" scroll |
| `E700 = 0x00` | default scroll mode (LAB_92af tail) |
| `E102 |= 0x28 & ~0x04` | set bit 5 (level_complete → LAB_40da) + bit 3 (end_credits → LAB_46d5), clear bit 2 |

No trampoline needed: the main-loop dispatcher (0x4085) drives `LAB_40da`
(fade/reset/`sub_516c`/`load_logo_tiles`/stream reload via `sub_940c`/music),
clears bit 5 (0x4150), then on the next frame dispatches bit 3 → `LAB_46d5`.

### Answers to the key questions
1. **0x005C / 0x0059** = **LDIRVM** (RAM→VRAM) / **LDIRMV** (VRAM→RAM). A
   stash/restore pair: 0xE800 → VRAM 0x3C00 (scratch), then VRAM 0x3C00 →
   0xE800. Lets the credits screen be pre-built into 0xEB00 without disturbing
   the live 0xE800 screen. (Sprint annotations FILVRM/SETWRT were wrong.)
2. **sub_9433(0xBBB4)** = `init_credits_stream`: points the level-stream engine
   at the credits data; sets E701/E702/E704/E706. Does **not** blit VRAM
   patterns. → `build_tile_screen` (sub_946e) then fills 0xE800.
3. **sub_946e** = `build_tile_screen`: 24× `sub_94c3` → assembles the 24×24
   credits tile screen into 0xE800 in one shot.
4. **E700 = 0x0C**: bit 2 = alternate end path (logo reveal, 0x980e →
   `copy_tile_column`); bit 3 = per-column VBLANK sync (`sub_9ae4`). Reveal
   phase only; cleared by `LAB_92af`.
5. **E710 = 0x20**: current_scroll_speed seed for the reveal phase (confirmed
   it is the scroll accumulator, per `scroll_velocity_ctrl`).
6. **sub_516c** = `reset_enemies_and_psg`: zeros the 5 sound slots at 0xE20C +
   GICINI → mutes PSG and stops all enemy-fire/sound channels.
7. **0x0059** (see Q1) = LDIRMV, VRAM 0x3C00 → RAM 0xE800.
8. **IX = 0xE700** (`scroll_state`). `(IX+0x57)` = ending-phase index (set
   0xD1 → next phase 0x11); `(IX+0x56)`/`(IX+0x50)` = phase sub-state.

The logo **pixels** come from `load_logo_tiles` (same as the title screen),
not from `LAB_91fd` — that was the missing piece.

### KB / tooling deltas
- New symbols: `copy_tile_column` (0x986E), `scroll_vram_inner` (0x9AA6),
  `ending_setup` (LAB_91fd/92af), `init_credits_stream` (0x9433),
  `build_tile_screen` (0x946E), `clear_credits_busy` (0x92CA).
- Updated `scroll_state` (E700 bits 2+3), `scroll_map_reader`,
  `scroll_vram_write` (narrowed range, cross-links).
- New screenshot capability: `tools/zanac_shot.py` + docs in
  `kb/guides/openmsx-control.md` §11 and `CLAUDE.md` (headless `-control stdio`
  can't screenshot; launch with the SDL renderer and connect via the socket).
