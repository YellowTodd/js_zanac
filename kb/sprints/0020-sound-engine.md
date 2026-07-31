---
id: "0020"
status: done
range: 0x4E7B-0x4F00,0x5189-0x5240
strategy: callgraph_leaf
budget_turns: 30
---

# Sprint 0020 — Sound engine: PSG track player and music data

## Goal

The PSG sound system (AY-3-8910 at ports 0xA0–0xA2) is completely unmapped.
This sprint identifies the music player architecture and locates all music data.

1. Find the **per-frame music player entry point** — the routine called each
   VBlank to advance PSG register state.
2. Map the **call hierarchy** from ISR → music player → PSG writes.
3. Identify **music data tables** (likely in ROM 0x8000–0xBFFF range, based on
   the dense data blocks visible in the source around lines 2190–2320).
4. Distinguish **music tracks** (title, intro, main, game-over) from **sound
   effects** (explosions, fire, pickup).
5. Decode at least one track's **header format** (tempo, channel pointers).

## Inputs

- `kb/symbols/0x4000-init/vblank_isr.md` — ISR calls `sub_4E7B` and
  `scroll_vram_write`; neither is the music player. Music player must be in the
  ISR or called from the main loop.
- `kb/symbols/0x5000-gameplay/reset_enemies_and_psg.md` — 0x516C: mutes PSG
  via GICINI (0x0093). PSG init path confirmed.
- Source lines 2190–2320: large DB blocks suspected to be PSG track data
  (bytes like 0xA0, 0xA2 match PSG port I/O patterns or command bytes).
- BIOS PSG calls: `GICINI` (0x0093), `WRTPSG` (0x0096), `RDPSG` (0x0099).

## Verification plan

**Headless — find music player by PSG watchpoint:**
```python
with ZanacGame.launch() as game:
    msx = game.client
    game.wait_for_title()  # title music should be playing

    # Watchpoint: capture every write to PSG address register
    msx.cmd("set ::psg_writes {}")
    wp = msx.cmd(
        "debug set_watchpoint write_io 0xa0 {} "
        "{lappend ::psg_writes [reg PC]}"
    )
    time.sleep(0.1)   # capture one frame of PSG writes
    msx.cmd("debug break")
    writers = msx.cmd("set ::psg_writes").split()
    # deduplicate and print unique PCs
    for pc in sorted(set(int(x) for x in writers)):
        print(hex(pc))
    msx.remove_watchpoint(wp)
```

The cluster of PCs will identify the PSG driver.

**Static — decode music data:**
- Source lines 2190–2330: scan for patterns that match a PSG track format
  (e.g., register-number / value pairs, tempo bytes, loop markers).
- The `0xA0` bytes scattered in the data (~10 occurrences) are suspicious —
  either literal 0xA0 values, or an end-of-command marker in the track format.
- Look for a table of track pointers (likely a list of 16-bit LE addresses
  into the track data, indexed by track number 0–5 or similar).

## Hypotheses to test

- Is there one music player or separate handlers per track?
- Does the ISR call the music player directly, or does the main loop?
- Are sound effects mixed at the PSG level or handled by a separate channel
  manager?

## Expected new KB files

- `kb/symbols/0x????-sound/psg_player.md` — music player entry point
- `kb/data/psg_track_data.md` — track table and format
- `kb/features/sound-engine.md` — architecture overview

## Summary

**All five goals answered by static analysis.**

### Goal 1: Per-frame music player entry point
**`psg_sound_tick` (0x4E7B)** — already in KB as `fire_trigger_and_ppt_manager`,
but that name and interpretation were wrong (see correction below). Called from
`vblank_isr` every frame.

### Goal 2: Call hierarchy
```
vblank_isr → psg_sound_tick (0x4E7B)
  ├─ fire-sound: GICINI(7,0xBF) via 0x5182 → return
  ├─ slot loop (5 × stride 27): sub_5099 (note seq) + sub_50D2 (amplitude)
  └─ GICINI loop: write shadow regs 0xE201-0xE20B → PSG R0-R10
```

### Goal 3: Music data tables
- **Shadow PSG registers**: 0xE200–0xE20B (11 bytes). Engine updates these
  each frame; `psg_sound_tick` flushes all to hardware at frame end.
- **Event pointer table**: 0x5234/0x5236 — 27 entries × 2-byte LE addresses.
  Indexed via `play_sound_event` (0x5189) → `sub_5199`.
- **PSG frequency table in RAM**: 0xF200 — 12 notes × 10 octaves, built at
  cold boot by `init_psg_freq_table` (0x513F).
- **Track data blocks**: dense packed from ~0x52E2–0x59D7 (the large DB sections).

### Goal 4: Music tracks vs SFX
Known assignments from call-site analysis:
| Event | Data | Type |
|-------|------|------|
| 3     | 0x543C | Title music (called in `title_intro_seq`) |
| 4     | 0x551C | Attract/game-over music (called in `sub_4663`) |
| 0x12  | TBD    | Explosion SFX (from `handler_type80_base_damage`) |

Total 27 event slots; others TBD.

### Goal 5: Track header format
Each event entry:
```
Byte 0:    N = number of voices
For each voice:
  Byte 0:  slot descriptor D  (slot offset = D × 26 in 0xE20C table)
  Bytes 1-8: 8 init bytes → copied to slot[0..7]
```

Sound data command bytes in track data follow a pattern of note values (0x19–
0x4x range) interleaved with command bytes (0x80–0xEF). Full command format
decode is pending live verification.

### Corrections
- **`sub_4E7B`** renamed `psg_sound_tick`. Prior name `fire_trigger_and_ppt_manager`
  was misleading — it's the complete per-frame sound engine, not just fire sound.
- **0xE20C** = PSG sound-engine voice slots (NOT "player_projectile_table").
  The "3 active slots at game start" from sprint 0018 were the 3 tone channels
  of the title music, not fire-weapon projectiles.

### New KB artefacts
- `kb/guides/sound-engine.md` — full architecture reference
- `kb/symbols/0x4000-init/sub_4e7b.md` — updated (name + full analysis)

### Still open (for sprint 0020 live follow-up)
- sub_5099 (note sequencer) full decode
- sub_50D2 (amplitude envelope) full decode  
- Slot descriptor stride discrepancy (D×26 vs init stride 27)
- Music command byte table at 0x4F6C (JP table — 15 command handlers)
- Full event map (events 1, 2, 5–17, 19+)
