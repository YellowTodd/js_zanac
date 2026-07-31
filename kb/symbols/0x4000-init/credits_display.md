---
address: 0x46D9
end: 0x4774
kind: routine
name: credits_display
confidence: confirmed
inputs:
  IX: must be 0xE100 (game-state base; set by the 0x46D5 entry)
outputs: {}
clobbers: [AF, BC, DE, HL, IX, IY]
calls: [0x4ACE, 0x4775, 0x47AA, 0x5BDD, 0x42ED, 0x0053, 0x5BFC, 0x46A8, 0x41CB, 0x43D2, 0x4042]
called_by: [0x46D5, 0x4690]
tags: [credits, ending, input, text]
sprint: "0046"
---

# credits_display  (LAB_ram_46d9)

## Summary

Entry to the end-credits / staff-roll display, reached from the main game loop
when `E102` bit 3 is set (game beaten). `LAB_46D5` (0x46D5) sets `IX = 0xE100`
and falls into `LAB_46D9`, which resets the credits cursor, saves the hi-score,
and runs the staff-credits loop until ESC returns to the title screen.

The full input/flow narrative (key handling, page cycling, ESC-to-title) lives
in `kb/guides/input-state-machine.md` §"End-credits sequence"; this entry covers
the routine structure.

## Entry — 0x46D9

```
46D5  LD IX,0xE100              ; (LAB_46D5) game-state base
46D9  LD (IX+0x5C),0            ; E15C = 0  → credits entry index = first
46DD  CALL 0x4ACE              ; compare_save_hiscore (see below)
                                ; ── falls into the page loop at 0x46E0 ──
```

`0x4ACE` (`compare_save_hiscore`, out of this sprint's range) does a 3-byte
compare of the current score (E103) against the hi-score (E106); if
score ≥ hi-score it copies E103→E106. Confirms the sprint hypothesis that
0x46D9 saves the hi-score on entry. See [[compare_save_hiscore]].

## Page loop — `LAB_46E0` (0x46E0)

Per page: `IX+0x5D` (E15D) = starting text row (5); `HL` walks the **entry
control table at 0x4775**; `IY = 0xE185`. For each entry it skips `B`
length-prefixed strings into the **string table at 0x47AA**, then centre-aligns
and prints the target string to the name table:

- column = `((len + 2) >> 1)` complemented + 0x0D  → stored at `IY+0`
- right edge stored at `IY+0x18`
- VRAM address computed via `0x5BDD` / `0x42ED`, written with `WRTVRM` (0x0053),
  characters streamed with `0x5BFC`.

Strings decoded from 0x47AA include `GAME DESIGN`, `PROGRAM`, `GRAPHICS`,
`SOUND`, `DIRECTOR`, `JANUS`, `JEMINI`, `COMPILE`, `WAO`, `MOO`, `MIYAMOTO`,
`YORIKI`, `THANKS`, `PAL`, `MUSIC`, `LUNARIAN`, plus logo tile rows (0xB0–0xE6).

A `0xFF` terminator ends the entry list for a page; a second byte selects the
inter-page delay (`0x190` normally, `0x4B0` for the final page which also resets
E15C to 0 to loop the roll).

## Page pacing & exit — `LAB_475C` (0x475C)

```
475C  CALL 0x46A8; JR C,475C   ; wait BC frames OR until fire (carry) → recycle entry
4761  CALL 0x41CB              ; clear_title_state
4764  LD BC,0x50
4767  CALL 0x46A8; JR C,4767   ; 80-frame settle, fire keeps it up
476C  CALL 0x43D2              ; check_esc_key (row 7 bit 2 = ESC)
476F  JP Z,0x4042             ; ESC held → title screen (LAB_4042)
4772  JP 0x46E0              ; else → show credits again from the top
```

`0x46A8` (`wait_fire_or_timeout` variant) keeps the background scroll alive
(`sub_9480`/`sub_9393`) and returns carry on a SPACE/SHIFT/Z/joystick edge so
fire cycles entries; STOP still pauses inside it.

## Live confirmation (sprint 0046)

Driven from `savestates/game-end.oms` (round-8 boss kill → ending): after the
main loop processed `E102` bit 5 then bit 3, **0x46D9 was reached** and the
hi-score save at **0x46DD** fired once on entry. A screenshot of the running
display shows the centred staff roll — **"GAME DESIGN", "JANUS", "MOO",
"JEMINI"** — over the round-0 terrain scroll, with the HUD at **ROUND 0** and
**TOP = SCORE = 2211200** (hi-score promoted). Holding **ESC** during the display
returned to the title (`0x4042` reached). `tools/sprint0046_verify.py`.

## See also

- `kb/guides/input-state-machine.md` — full end-credits key/flow narrative.
- `ending_setup` / `init_credits_stream` (0x9000 area) — what sets E102 bit 3
  and loads the credits scroll/graphics before this routine runs.
- `wait_fire_or_timeout.md`, `clear_title_state.md`, `check_esc_key.md`.
