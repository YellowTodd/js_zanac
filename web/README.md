# Zanac — browser port

A native JavaScript reimplementation of Zanac (Compile, MSX1, 1986), written
against the disassembly and knowledge base in this repository. No Z80 code runs:
the game logic is JS, and the assets are extracted from the cartridge ahead of
time.

## Run

Any static file server works — ES modules need HTTP, not `file://`.

```bash
node tools/serve.mjs            # http://localhost:8000/ (--root/--port to override)
python -m http.server 8000 --directory web   # equivalent
```

In VS Code, **F5** does both: it starts `tools/serve.mjs` and opens the port in
Chrome with the debugger attached (breakpoints in `web/src/**` work; stopping
the session kills the server). Alternate configs launch Edge or the default
browser — see `.vscode/launch.json`.

Controls: arrows or WASD to move, SPACE/SHIFT for the shot, Z or X for the
fire weapon, **F1** to pause (F1+F2 pauses silently, without the caption),
ESC held at the title screen to continue from the last round reached.

### Debug round select (not in the ROM)

Press **`** (backquote/tilde) on the title screen to toggle debug mode — the
title stays completely stock until you do. With it on, **0-8** picks a
starting round and the choice shows under the title text; round **8** is the
quick way to reach the ending, round **0** the hidden warp stage.

The selection survives into the game exactly the way the ESC continue does
(`title_screen_init` only forces round 1 when nothing else armed it) and
re-arms per title screen; the mode itself stays on until you press backquote
again. Backquote rather than a letter because D/S/A/W are movement, Z/X are
fire and Shift/Space are the shot. Everything lives in `src/game/debug.js`,
which the ported routines never call into.

## Assets

`assets/` is generated — regenerate after any change to the extractor:

```bash
python tools/export_assets.py
```

| File | Contents |
|------|----------|
| `gfx.png` | the nine graphics blocks, RLE-decoded — 8.3 KB payload; the image itself is a readable tilesheet |
| `data.png` | 32 KB address-identity payload of the cartridge's *data* bytes (code zeroed); the image is a byte map |
| `manifest.json` | block offsets, payload byte lengths, palette, provenance |

The exact payload bytes ride in a private PNG chunk, `zaNc` (a zlib stream the
loader inflates with `DecompressionStream('deflate')` in the browser, node:zlib
headless). No canvas is involved, so there is no premultiplied-alpha hazard.
Because the payload is not in the pixels, the **visible image is free to be
useful**: `gfx.png` renders as the actual tilesheet (charset, ZANAC logo,
terrain tiles, all 64 sprites) and `data.png` as a byte map — one pixel per ROM
byte, 256 per row, code bytes black — so you can see at a glance which address
ranges survive the code mask.

`data.png` keeps ROM addressing so game code can reference tables with the same
`0xNNNN` constants the knowledge base uses — `rom.byte(0x945C)` is literally
`stage_stream_ptr_table`. Tables the disassembler mis-renders as instructions
have to be listed in `KEEP_RANGES` (`tools/export_assets.py`) or the mask zeroes
them; see corrections 30, 31, 34 and 35.

## Layout

```
src/screen.js      SCREEN 2 display model + pure RGBA rasteriser
src/assets.js      manifest/gfx/data loading, DataRom address view
src/input.js       keyboard -> the engine's active-low 0xE100 input byte
src/sound.js       sound-event front-end (PSG synthesis pending)
src/game/flow.js   cold_start / main_game_loop / title_screen_init
src/game/title.js  title attract sequence and logo swirl
src/game/hud.js    BCD score rendering
src/game/scroll.js map-script interpreter + tile-row builder + ring blit
src/game/entity.js    26-slot entity pool, entity_update, sprite shadow
src/game/player.js    player ship, steering, the normal shot
src/game/collision.js hitboxes, check_col_clear, entity_post sweep
src/game/debug.js        port-only dev affordances (round select), off by default
src/game/base.js         base encounter controller + victory ceremony
src/game/base_segment.js base segments 73-79: shutter, tiles, firing
src/game/loop.js   frame-scheduling helpers
src/main.js        browser entry: rAF driver + canvas blit
```

Playfield geometry, derived from 0x9A5B and 0x9AA6 rather than the KB: the map
reader assembles a 32-tile row at 0xEA40 of which bytes 8..31 are visible; those
24 tiles become one row of a 24×24 ring; `scroll_vram_write` emits 24 tiles per
name-table row. So the playfield is columns 0–23 and the status panel owns
columns 24–31.

Routines that block on `wait_frames` in the original are generators here — one
`yield` is one frame — so control flow keeps the shape of the assembly and stays
diffable against the KB.

## Headless verification

The display model and game modules have no DOM dependency, so they run under
Node and can be checked as PNGs without a browser:

```bash
node tools/render_check.mjs C:/Temp/zanac-gfx     # tile set, sprites, sprite-per-line limit
node tools/title_check.mjs  C:/Temp/zanac-gfx     # title sequence, frame by frame
node tools/scroll_check.mjs C:/Temp/zanac-gfx 1   # scrolling playfield for a round
node tools/mapscript_check.mjs                    # walk all nine map scripts
```

`mapscript_check` is the load-bearing one for the scroll engine: a wrong operand
length desynchronises the program counter immediately, so a clean walk of all
nine scripts — non-decreasing row triggers, valid command bytes, and the
R1→R2→…→R7 / R7→R7 / R0→R8 jump chain — proves the interpreter consumes the
stream exactly like `map_script_step`.

## Luster trio entry structure (resolved)

`entity_jump_table` is exactly right - 16/0x7BEB, 17/0x7C8A, 18/0x7CB3
(re-dumped from the ROM words at 0x70B7; an earlier read used base 0x70B9 and
appeared shifted by one). The three inits then all fall into a shared tail at
0x7BFF - random side pick, 0x7C complement child, sat 0x74 - ending in a
`SUB 0x92` switch on the now-active type byte for the per-type finish. Ported
in `src/game/enemy.js` (`runLuster`).

## Fire-box weapon digits (user-reported, fixed)

The round-1 pair now renders exactly like the original: red "2" on the left
box, "1" on the right (idol table 0xAA68 = `02 01 ...`, indexed by the idol
cursor each wide placement consumes). Three pieces were needed: the 0x87AB
body (digit into the scroll ring + idol-table load + per-type HP), the 0xE71D
allocation cursor in `place_tile_group` (consumed on blocked placements too),
and reading the slot's +0x03 cursor *before* the sprite-name overwrites it.
The earlier "boxes never spawn" confusion was a test artifact - headless bots
game-overed before map row 129 and the run silently restarted at the title.

## Palette choice

`tools/zanac_assets.py` ships the measured NTSC TMS9918A palette (the
WebMSX/blueMSX set) rather than the datasheet values recorded in
`kb/guides/vdp-tms9918a.md`. The datasheet set puts medium green (33,200,66)
and dark green (33,176,59) nearly on top of each other, which flattens Zanac's
grass - colour byte 0xC2, dark-green figure on medium-green ground - into one
bright tone; the measured set (2 = 3EB849, 12 = 3AA241) restores the contrast
seen in reference captures. Not a KB error: the KB documents the datasheet
faithfully; this is a rendering preference. Swap the table back if you want
datasheet colours.

## Corrections found while porting

Each of these is written up in the KB file it belongs to; `kb/guides/port-corrections.md`
indexes them.

- **`logo_tile_rows` stride is 19, not 25.** `kb/data/logo_tile_rows.md` recorded
  "stride 25 (0x19)", mixing decimal and hex. The index math at 0x5BC3 gives
  19 decimal, which makes the table end exactly at 0x4897 (one byte before
  `entity_update`), puts the logo tiles in unbroken 0xB0..0xE6 order, and makes
  row 5 the all-blank erase strip the swirl needs. With 25 the logo renders as
  disconnected fragments and the erase pass reads code bytes.
- **`gfx_logo_colors` decodes to 488 bytes (61 tiles), not 232 (29).** Hand-decoding
  the 12 compressed bytes at 0x5EF0 gives runs of 256+40 white, 144 grey and 48
  dark red — matching the 61 tiles the bitmap block defines, with the last six
  (0xE7..0xEC) being the red PONYCA mark.
- **`render_score_bcd` writes 7 tiles, not 6:** six space-suppressed BCD digits
  plus a literal `'0'` (0x49D6), so scores are stored in units of ten.
- **Column-descriptor ADVANCE records are 2 bytes, not 4.** `b0 == 0xFF` at
  0x9911 adds the count to the slot's column and resumes at the byte *after*
  `b0`, reinterpreting the following two bytes as the next record's
  `[cnt][b0]`. Only LINK and COLUMN records are the 4 bytes
  `tile_column_data_region1.md` describes.
- **`map_script_init` seeds `level_row_ctr` to `trigger - 1`** (0x9424), so the
  first step lands on the first command. Starting the counter at 0 skips every
  command whose trigger is row 0.

- **`vel_dir_table` entries are (Y, X), not (X, Y).** The first word goes to
  +0x08/+0x09, which `entity_table.md` documents as the *Y* velocity;
  `set_velocity_from_dir.md` labels the pair the other way round, which mirrors
  every direction. With (Y, X) all eight compass directions agree with
  `xvel_table` and the 0x43A0 selector arithmetic — e.g. holding up gives
  selector 5 → direction 12 → (−128, 0) → up.
- **`place_tile_group` consumes `1 + 1 + 3 × (descriptor & 0x1F)` bytes.** The
  descriptor's low five bits are the record count (`B` at 0x95F7), and each
  record costs three stream bytes on both paths — placed at 0x963A, skipped by
  the three `INC DE`s at 0x960C. Getting this wrong desynchronises a greeble
  stream rather than the script.

- **`check_col_clear` (0x9B22) is also the allocator.** Its first phase walks
  slots 25 down to 5 and returns as soon as it finds an inactive one, leaving HL
  on that slot — which is what `place_tile_group` then writes the new structure
  into. Reading it as a pure predicate leaves the placement code with nowhere to
  put anything.

## Play state

The full game loop closes: title -> round 1 with two terrain layers, ground
structures and aimed airborne attackers -> shot kills with explosion animation,
SFX events and BCD scoring -> player deaths (11-frame explosion, ALC easing,
lives) -> game over -> back to the title with the score carried in the header.
The right-hand status panel (columns 24-31) renders TOP/SCORE/ZANAC/LEVEL/ROUND
with live values, per `draw_hud_labels` (0x4BD4) and `update_status_bar`
(0x4C4D).

## Not yet ported

(Refreshed 2026-07-30, after the base/boss slice. The base encounter is now in: placement via `place_tile_group` bit 7,
the four-phase controller `base_tick` (0x8F5E) with its scroll stall and
"TIME" countdown, the seven segment types with their shutter animation,
per-type tile blitters and firing geometry, the projectiles they fire
(42/43/45), the type-11 wave spawner, and the victory ceremony.
Everything else round 1 touches was already byte-faithful: structures, craters, orbs and warps,
boxes and pickups, all eight fire weapons, the walker's kill lottery, spawning,
collisions, HUD, and the PSG.)

**Airborne enemy types without handlers.** The spawn controller is wired and
produces the full ROM list; types with no handler fly as generic movers or sit
inert. Landed 2026-07-30: the veybar family (22–25), the edge swoopers (26–29), the
ten-type ground-gun family (**46–55**, one handler at 0x8094), the duster (10),
the lead homing bullet (20) and the light bar (21). Also in: the descender/dart family
(**56–59**, sharing 0x81AC/0x81C3 — a type 58 splits into a three-way volley
of type-59 darts aimed at the player) and the curving shot (**41**, which
sums a fixed forward velocity with a rotating perpendicular one). The final
batch landed 2026-07-30: the missile umber (9), the stealth pairs that merge
on the player's row (30-33), the bursters (34/65/66, including 66's five-dart
aimed shotgun), the sixteen-hit flasher (36), the **1-UP** (62 - the walker
lottery's jackpot, which re-uploads its two sprite frames into pattern 0), the
spawn-list re-roller (64) and the phase charger (67). **Every entity type the
spawn system can produce now has its handler.**

**Map-script commands 1, 3 and A** are in (2026-07-30). Command 1 turned out
to be **scripted enemy waves**, not tile placement: each 3-byte record becomes
a type-69 emitter carrying `(enemy type, count, interval)`, and command 0 falls
into the same body when its control byte has bit 2 set. That alone took a
round-1 entity census from 20 distinct types to 26. Command 3 relocates a
column-group descriptor and disables the source; command A repaints the
crater tiles' colours so wreckage matches the terrain.

**Round transitions** are in (2026-07-30). `level_complete_handler` (0x40DA)
now runs for real: `reset_entities` over slots 5–25 only, the transition SFX,
the dissolve-out, a 100-frame blank hold, the three tile-reload paths (rounds
1–7 reload nothing), 24 pre-run map-script steps, the dissolve-in, and the
0xE132 reset. The black warp orb raises 0xE102 bit 5 into that path instead of
jumping the script in place — and map command 9, which is what actually chains
rounds 1→7, correctly skips the column-slot wipe (it enters at 0x941B).

**Ending & credits** (subsystem L) are in (2026-07-30): the three-beat finale
(logo screen built from the 0xBBB4 mini-script and revealed column-pair by
column-pair with the ending theme; the 0xBBFD letter rows arriving with
explosion bursts; the credits arming through a real round-8 -> round-0
transition), and the staff roll itself — centred pages from the 0x4775/0x47AA
tables with per-row blit shields, fire extending a page, ESC to the title, and
the ZANAC logo typeset by the same printer from the logo tile rows. The ship
stays flyable underneath, as in the ROM.

**Sound edges** are closed (2026-07-30). The shot SFX now uses the ROM's own
`3 + (0xE10F >> 2)`, so the pew rises 13 -> 14 -> 15 as the main shot gains
streams. And `fire2_special_table` turned out not to be a sound feature at
all: its records go to `sub_97BC`, so **taking fire weapon 2 summons an enemy
wave** whose composition depends on shot level and shifts once the round
reaches 5 — see the KB entry.

The **pause** (0x4DA5) is in too: F1 freezes the game with the blinking
PAUSE caption and mutes the PSG through `mute_sound` (so the tune resumes
mid-phrase), and holding F2 as well gives the ROM's silent variant. Leaving it
needs a fresh press, exactly as the ROM's latch demands.

The **scoring extras** are in as well (2026-07-30): `add_score` tail-calls the
new-record check and the extra-life loop, so the TOP row now flashes when the
record falls (event 9) and the player gains a life at **20000 and then every
60000** (event 8), with the score pegged at 999999 rather than wrapping.

### Measuring what is left

`python tools/port_coverage.py` cross-references the ROM addresses the port
cites in its comments against the KB's routine ranges. It is a lower bound (a
ported routine with no citation counts as missing) but it is what surfaced the
last real gap — types 84-86's `handler_type84_wide_variant`, 109 bytes of
gameplay code that had no port at all.

What it still lists as unported is now almost entirely **platform code a
native rewrite deliberately replaces**: `output_slot_to_psg`, `sat_dma_to_vram`,
`decompress_block` (done at build time in Python), `detect_slot`,
`vblank_isr`, `div_hl_e`/`mul_a_e`, the VDP register and interrupt helpers,
and the inline string printers.

With that, every routine and table the round-1-to-8 game path touches is
ported. What is left is deliberate: the 0xE102 bit-6 "run 64 frames then
restart the round" branch that nothing in the shipped scripts sets, and the
handful of base scenarios (`0xE157 & 0x1F` = 0x11 and friends) the map scripts
never select. There is **no demo/attract mode** in this ROM - an earlier note
here claimed one, but 0xE102 bit 7 is `go_to_title`, not a demo flag.
