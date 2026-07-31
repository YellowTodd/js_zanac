---
address: 0x94c3
end: 0x9534
kind: routine
name: map_script_step
confidence: confirmed
inputs:
  IX: "0xE700 (scroll_state base), set by caller (build_tile_screen / scroll_velocity_ctrl)"
outputs: {}
clobbers: [AF, BC, DE, HL, IY]
calls: [0x9ae4, 0x97e3, 0x5c2e]
called_by: [0x9477, 0x94c0]
tags: [scroll, level-map, map-script, interpreter]
sprint: "0056"
---

# map_script_step  (sub_94c3)

## Summary

The **per-column map-script interpreter** — the heart of subsystem D. Each call
advances the scroll by one map row and either builds one tile column (the common
case) or executes the next row-triggered **map command**. Driven once per visible
column by [[build_tile_screen]] (0x946E, ×24) and per frame by
[[scroll_velocity_ctrl]] (which falls through into 0x94C3 after the speed
accumulator carries).

Full stream/command format and the 13-command table: [[level_script_format]].

## Program-counter state (in [[scroll_state]], IX = 0xE700)

| Addr | Role |
|------|------|
| 0xE702 | `level_row_ctr` — absolute map-row counter, +1 per column |
| 0xE704 | `stream_ptr` — 16-bit LE map-script program counter (ROM 0xA65C–0xB7A5) |
| 0xE706 | `next_cmd_row` — 16-bit LE row trigger of the next pending command |
| 0xE701 | `stage_index` / round number (printed by cmd 8) |

## Analysis

Source 0x94C3–0x9534.

```
94C3  BIT 3,(IX+0) ; CALL NZ 0x9ae4   ; per-column VBLANK sync (scroll_sync)
94CA  HL=(0xE702); INC HL; (0xE702)=HL ; row counter ++
94D1  LAB_94d1 (loop):
        DE=(0xE702); HL=(0xE706); SBC HL,DE
        JP NZ 0x97e3                  ; row != trigger -> build ONE tile column, return
        ; row == trigger: execute next command
        HL=(0xE704); A=(HL); (IX+0xF)=A ; INC HL   ; fetch command byte, save whole
        A &= 0x0F                     ; low nibble = command 0..12
        CALL 0x5c2e                   ; dispatch via inline word table…
map_cmd_jump_table:  DB <13 LE words> ; 0x94EB (cmd 0..12 -> handler addrs)
```

`sub_5c2e` is the inline-table computed-jump dispatcher (also used by the
fire-weapon system): it pops the table address, indexes by `A×2`, and jumps to
the looked-up handler, restoring HL. Each of the 13 handlers consumes its
operands from HL and ends with `JP 0x97D5`.

### Converge point — `LAB_97d5` (0x97D5)
```
97D5  E=(HL); INC HL; D=(HL); INC HL   ; read next 2-byte row trigger
97D9  (0xE704)=HL                      ; advance program counter past it
97DC  (0xE706)=DE                      ; arm next trigger row
97E0  JP 0x94D1                        ; loop — may fire more commands this row
```

So every command record is `[handler-specific operands][next row : 2 bytes LE]`,
and several commands can fire on one row (triggers are non-decreasing).

### Tile-build path — `LAB_97e3` ([[scroll_precompute]], 0x97E3)
Taken when `row != trigger`: decrements `scroll_row`, calls
[[scroll_map_reader]] (0x9888) to assemble one 24-byte tile column into the
0xE800 buffer, and raises the DMA-ready handshake (E700 bits 0/1) for the ISR.

## Related entry points

- **`map_script_init`** (`sub_940c`, 0x940C; entered via `sub_9405` 0x9405 which
  first zeroes scroll speed 0xE710/0xE711): clears the 16 column-group slots at
  0xE2C0 (status 0x80), then `LAB_941b` reads the script's leading 2-byte trigger
  into 0xE706 (and trigger-1 into 0xE702 so the first command fires immediately),
  stores the program counter to 0xE704, and clears E700 bit 0.
- **`sub_9433`** (0x9433, cmd 9 target): given a new script pointer in HL,
  resolves the stage via [[resolve_round_from_ptr]] (0x9444 → `stage_stream_ptr_table`
  0x945C), stores 0xE701, renders the round digit (`0x4C68`), then `JP LAB_941b`
  to (re)start the interpreter on the new round's script.

## Live confirmation (sprint 0056)
`tools/scroll_confirm.py`: PC walked forward 0xA75B→0xA77A as triggers stepped
30→50→80→110; commands 2/5/8 dispatched; ROUND banner (cmd 8) fired once with
0xE701 = round 1. See [[level_script_format]].
