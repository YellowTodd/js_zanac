---
id: "0022"
status: done
range: 0xBFA0-0xBFC7
strategy: forward_from_caller
budget_turns: 25
---

# Sprint 0022 — Base encounter projectile system (close live-debug Q5/Q7)

## Goal

Finish the two remaining open questions from `live-debug.md`:

**Q5/Q7:** Which entity handler or ISR path reads 0xE71E (the attack-list
pointer) and 0xE150 (base-active flag) to spawn base projectiles? Sprint 0010
identified the consumer candidates but could not confirm via read-watchpoint
(openMSX limitation at the time).

With `ZanacGame` now available, **inject** the base-encounter state directly
(write 0xE150 = 1, populate 0xE71E) rather than waiting for the scroll engine
to reach a base naturally.

## Inputs

- `kb/symbols/0x9000-scroll/base_encounter_ctrl.md` — `base_encounter_ctrl`
  at 0xBFCB reads 0xE150 bit 1; increments 0xE130 (base health counter).
- `kb/symbols/0x9000-scroll/place_tile_group.md` — writes 0xE150/0xE151/0xE71E.
- `kb/data/game_state_block.md` — 0xE150: base_encounter_flags; 0xE151:
  base_attack_count; 0xE71E: attack-list pointer.
- Sprint 0010 Q5: "the actual base-projectile dispatch uses 0xE71E (the
  attack-list pointer) via entity handler near 0xBFA0 — which uses (IX+0x25)."
- `kb/symbols/0x8000-enemy/handler_type11_base_spawner.md` — reads 0xE130.

## Verification plan

**Headless — synthetic base trigger:**
```python
with ZanacGame.launch() as game:
    game.wait_for_title(); game.start_game()
    msx = game.client
    time.sleep(2.0)   # let game settle

    # Install write-watchpoint on 0xE71E BEFORE injecting base state
    msx.cmd("set ::e71e_writer 0")
    wp71e = msx.cmd(
        "debug set_watchpoint write_mem 0xe71e {} "
        "{set ::e71e_writer [reg PC]; debug break}"
    )

    # Inject base-encounter state
    msx.write_byte(0xE150, 0x01)  # base_encounter_flags bit 0
    msx.write_byte(0xE151, 0x04)  # base_attack_count = 4
    # Write a fake attack-list: 4 × 2-byte tile addresses
    msx.write_memory(0xE71E, bytes([0x00, 0xA0, 0x20, 0xA0, 0x40, 0xA0, 0x60, 0xA0]))

    msx.cont()
    time.sleep(1.0)
    writer = msx.cmd("set ::e71e_writer")
    if writer != "0":
        print("0xE71E written by:", hex(int(writer)))
        print(msx.cmd(f"disasm 0x{int(writer)-4:04X} 10"))
    msx.remove_watchpoint(wp71e)
```

**Read-watchpoint on 0xE71E** — sprint 0010 could not do this (watchpoint
limitation at the time); retry:
```tcl
debug set_watchpoint read_mem 0xe71e {} {set ::e71e_reader [reg PC]; debug break}
```

**Static** — disassemble 0xBFA0–0xBFC7 fully; trace all reads of IX+0x25.

## Key questions

- Which entity type reads 0xE71E? (hypothesis: type 11, the base projectile
  spawner at 0x7AD4, which was confirmed to read 0xE130)
- What is the attack-list format at 0xE71E: tile addresses, spawn positions, or
  entity type codes?
- Does `base_encounter_ctrl` at 0xBFCB spawn projectiles, or only update health?

## Expected new KB files

- Updated `kb/symbols/0x8000-enemy/handler_type11_base_spawner.md`
- `kb/symbols/0x9000-scroll/attack_list.md` — 0xE71E format

## Summary

### Approach

Two passes: (1) ROM byte search for every instruction accessing 0xE71E or
0xE780; (2) natural gameplay with read watchpoints on 0xE71E and a write
watchpoint on 0xE150 (base activation), waiting for the scroll engine to
reach a base organically.

### Finding 1 — 0xE71E is only accessed by place_tile_group (confirmed)

Full-ROM search found exactly two accesses to 0xE71E:
- `LD HL, (0xE71E)` at 0x9626 — reads current write ptr
- `LD (0xE71E), HL` at 0x962F — updates write ptr after each entry

Both are inside `place_tile_group` (0x95ED). **No entity handler reads 0xE71E.**
The sprint 0010 hypothesis that "an entity handler near 0xBFA0 reads 0xE71E" was incorrect.

### Finding 2 — Attack-list entry format: 4 bytes (16-bit entity slot addr + 2 unknown)

Natural-gameplay watchpoint fired at 0x9626 during a base encounter. Registers
at that moment (IX=0xE700, IY=0xE2E0, HL→0xE780, DE=0xE620):

```
9624  EX DE, HL          ; HL ↔ DE
9626  LD HL, (0xE71E)    ; HL = 0xE780 (attack-list write ptr)
9629  LD (HL), E         ; write entity-slot-addr low byte
962A  INC HL
962B  LD (HL), D         ; write entity-slot-addr high byte (0xE6_)
962C  INC HL × 3         ; advance ptr by 4
962F  LD (0xE71E), HL    ; update ptr
```

Old HL = 0xE620 = entity slot 25 base. So each entry stores the **16-bit LE
entity slot address** of a ground-structure entity that forms a base column.

### Finding 3 — 0xBFA0 block fully decoded

| Address | Subroutine | Function |
|---------|------------|---------|
| 0xBFA0 | sub_bfa0 | Allocates entity slot via 0x4496; clears spawn_trigger (0xE125 bit0 when IX=0xE100); writes type 0x44 hex (=68 dec) |
| 0xBFAB | sub_bfab | LD HL,0xE12E; CALL 0xBFCB; SET spawn_ctrl bit0 |
| 0xBFB3 | sub_bfb3 | LD HL,0xE12E; CALL 0xBFC2; SET spawn_ctrl bit0 |
| 0xBFBF | sub_bfbf | LD HL,0xE130; falls into SUB_bfc2 |
| 0xBFC2–0xBFF4 | base_encounter_ctrl + display tail | As in separate MD |

No `CALL 0xBFA0` found in ROM — it must be reached via indirect dispatch (RST/JP table).

### Caller map (from search)

| Target | Callers |
|--------|---------|
| 0xBFAB | 0x8F58 (enemy handler), 0x9334 (scroll engine) |
| 0xBFB3 | 0x8371 (enemy), 0x8E1A (type-80 base damage), 0x90BF (scroll) |
| 0xBFBF | 0x9329 (scroll engine) |

### What remains unknown

1. **Who reads the attack list at 0xE780?** It doesn't use 0xE71E. The consumer
   presumably loops 0xE152 times over 0xE780+ (4-byte entries), using the entity
   slot addresses to coordinate the base encounter. The attack-list consumer
   routine has not been located.
2. **Type 68 (0x44)** spawned by sub_bfa0 — role in base encounter not decoded.
   Handler at 0x77A1 (currently guess in entity_jump_table).

### New KB artefacts

- `kb/symbols/0x9000-scroll/attack_list.md` — attack list format and location
- `kb/symbols/0x9000-scroll/sub_bfa0.md` — full decode of 0xBFA0–0xBFF4
- `kb/symbols/0x9000-scroll/place_tile_group.md` — updated with attack-list write sequence
