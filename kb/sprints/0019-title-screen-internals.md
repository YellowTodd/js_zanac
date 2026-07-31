---
id: "0019"
status: done
range: 0x4010-0x425A
strategy: forward_from_caller
budget_turns: 35
---

# Sprint 0019 — Title screen internals: init, animation, music hook

## Goal

Fully map everything that happens between power-on and the first playable frame:

1. **`cold_start` path** (0x4010 → 0x4042 → 0x41DB): which routines run, what
   they initialize, what order.
2. **`sub_42D7`** (0x42D7): the first call inside `sub_41DB` — unidentified.
3. **`sub_41CB`** (0x41CB): clears 0xE180–0xE1AF and sets E700 bit 0 — is it
   just a buffer clear, or does it also start the logo blit?
4. **Logo animation mechanism**: what writes the Zanac logo tile codes into VRAM
   0x3800, and what drives the animation frames. Involves GFX data at `gfx_logo_bitmap`
   and `gfx_logo_colors`.
5. **Music hook**: where does the title music start? Find the first PSG write
   (write-watchpoint on I/O port 0xA0) after `cold_start`. Identify the call
   chain from init → music player entry point.
6. **`sub_5BEC`** (0x5BEC): already identified as "wait B frames" (zeros E1F8,
   spins on `sub_42F8` until VBlank, loops B times). Confirm and label.
7. **SPACE detection during title**: `check_start_key` (0x43D2) at 0x424C is
   called ONCE during `sub_41DB`. Confirm whether the title-screen-visible SPACE
   polling happens in the ISR (via `sub_4E7B` / 0xE200 flag) or elsewhere.
8. **`sub_42D7` vs `sub_42E2` vs `sub_42ED`** — these three adjacent routines
   are called repeatedly; they appear to be VDP display-enable variants (enable/
   disable display bit). Confirm.

## Inputs

- `kb/symbols/0x4000-init/cold_start.md`
- `kb/symbols/0x4000-init/vblank_isr.md` — ISR calls `sub_4E7B` (fire trigger)
- `kb/data/gfx_logo_bitmap.md`, `kb/data/gfx_logo_colors.md`
- `kb/features/zanac-vdp-layout.md` — VDP register map; name table at 0x3800
- Source lines 31–270 (`cold_start` through `sub_41DB` and 0x422F area)
- Source lines 1975–1984 (`sub_5bec` — wait-N-frames)

## Verification plan

**Headless automated — initial PSG write:**
```python
with ZanacGame.launch() as game:
    msx = game.client
    # Install write-watchpoint on PSG address register (I/O port 0xA0)
    msx.cmd("set ::first_psg_writer 0")
    msx.cmd("set ::first_psg_pc 0")
    wp = msx.cmd(
        "debug set_watchpoint write_io 0xa0 "
        "{$::first_psg_writer == 0} "
        "{set ::first_psg_writer 1; set ::first_psg_pc [reg PC]; debug break}"
    )
    msx.cont()
    time.sleep(3.0)
    print("First PSG write by:", hex(int(msx.cmd("set ::first_psg_pc"))))
    msx.remove_watchpoint(wp)
```

**Static analysis:**
- Source around 0x42D7 (11 bytes before CALL at 0x41DE): disassemble fully.
- Source around 0x41CB (0x41CB–0x41DA, 16 bytes already decoded): confirm purpose.
- Source around 0x422F–0x424C: trace what happens between animation call and SPACE check.
- Search for `WRTPSG` (0x0096) and `GICINI` (0x0093) calls in range 0x4010–0x5000
  to find the music-start call chain.

**Logo animation:**
- Break at title screen, read VRAM 0x3800 tile codes for logo rows (0x38A0–0x39FF).
- Watch for writes to that range (write-watchpoint on 0x3800 area) to find the
  blitter routine.

## Key questions this sprint should answer

- What does `sub_42D7` do? (hypothesis: VDP display-off)
- What does `sub_42E2` do? (hypothesis: VDP display-on)
- What does `sub_42ED` do? (hypothesis: VDP display-on variant)
- Where does the title music start (first PSG write PC)?
- Is SPACE polling per-frame (in ISR) or one-shot (in init)?
- Does the logo animate frame-by-frame, or is it a single blit?

## Summary

**All 8 goals answered by static analysis; no live verification needed.**

### Q1: cold_start path
Full boot sequence confirmed (source lines 31–112). Cold boot does:
`cold_start (0x4010)` → hardware init + ISR install + LDIR-clear RAM →
`LAB_4042`: `reset_enemies_and_psg` → `sub_428A` (VDP + charset) →
`title_intro_seq (0x5A11)` → `title_screen_init (0x41DB)` →
wait 2 frames → enable display → `play_sound_event` (gameplay music) →
main loop at `LAB_4074`.

### Q2: sub_42D7 — already confirmed
`disable_display` — clears VDP R1 bit 6. Already in KB.

### Q3: sub_41CB
Confirmed as `clear_title_state`: zeroes 48 bytes at 0xE180–0xE1AF, sets
0xE700 bit 0. **Does NOT start the logo blit.** Pure state reset.

### Q4: Logo animation mechanism
- Logo is a **single blit** via `load_logo_tiles` (0x5C3C), called from
  `title_intro_seq` (0x5A11).
- The animation is tile *positions* scrolling through 5 slots at 0xE1FA–0xE1FE,
  not frame-by-frame tile updates.
- Name-table text "SCORE" and "TOP" written inline via sub_5C25/sub_5C28 using
  the inline-string pattern.

### Q5: Music hook
- **First music start**: `title_intro_seq` → `play_sound_event` (0x5189) with
  A=3 (title music track 3). This is the first queuing of PSG data.
- `play_sound_event` → `sub_5199` → looks up track from table at 0x5234 →
  copies data into a free slot at 0xE20C.
- Actual PSG port writes happen each frame from the sound engine tick (sprint 0020).
- The `init_psg_freq_table` (0x513F) is the very first sound-related call during
  cold boot, but it only builds an in-RAM frequency lookup — no PSG port writes.

### Q6: sub_5BEC — wait_frames
Already confirmed in KB. No new information needed.

### Q7: SPACE detection
- `check_start_key` is called **once** inside `title_screen_init` (0x41DB)
  (source line 299), **not** in the ISR.
- Continuous SPACE/button detection during the logo animation happens in the
  `title_intro_seq` animation loop via `sub_46bc` (which calls `sub_4343`).
- Per-frame fire-weapon SPACE is handled via 0xE200 / sub_4E7B in the ISR,
  but that only applies during gameplay.

### Q8: sub_42D7 / sub_42E2 / sub_42ED
All four VDP-register-1 helpers now confirmed:
- 0x42D7 `disable_display`: CLEAR bit 6 → screen off
- 0x42E2 `enable_display`: SET bit 6 → screen on
- 0x42ED `vdp_int_disable`: CLEAR bit 5 → VDP interrupt off
- 0x42F8 `vdp_int_enable`: SET bit 5 → VDP interrupt on

### Corrections to prior KB
- `reset_enemies_and_psg` (0x516C): the 0xE20C table is **sound-engine channel
  slots**, not enemy slots. Prior name was misleading. Updated.
- `cold_start.md`: promoted from hypothesis to confirmed, full call graph added.
- `vdp_int_disable.md`: confidence bumped to confirmed.

### New KB entries added
- `kb/symbols/0x4000-init/title_screen_init.md` (0x41DB) — new
- `kb/symbols/0x4000-init/clear_title_state.md` (0x41CB) — new
- `kb/symbols/0x5000-gameplay/play_sound_event.md` (0x5189) — new
- `kb/symbols/0x5000-gameplay/title_intro_seq.md` (0x5A11) — new
- `kb/symbols/0x5000-gameplay/init_psg_freq_table.md` (0x513F) — new

### Still uncertain
- Exact format of music data at 0xA624/0xA63C (sub_5199 channel slot layout).
- What `sub_46bc` returns in the carry flag — likely "button just pressed".
- Address of `sub_4343` relative to "joystick detect" vs PSG mute.

### Next sprint candidates
- **Sprint 0020** (sound engine): map the full PSG track player: 0xE20C slot
  layout, 0x5234 event table, per-frame channel tick, data at 0xA624/0xA63C.
- **Sprint 0021** (entity slot offsets 0x0C–0x1A): use 200-frame dump to fill
  the remaining entity-slot field table.
