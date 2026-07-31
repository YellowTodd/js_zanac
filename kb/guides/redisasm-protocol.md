# Disassembly patch protocol for `source/zanac.asm`

This guide documents how to decode DB-block code regions in `source/zanac.asm`
using `tools/redisasm.py` and verify the result is ROM-identical.

## Tool

**`tools/redisasm.py`** — generic, subcommand-based patch tool.

```
tools/redisasm.py checkpoint
tools/redisasm.py patch     --before REGEX --after REGEX --start ADDR --end ADDR
tools/redisasm.py data      --before REGEX --after REGEX --start ADDR --end ADDR [--label NAME]
tools/redisasm.py add-label --addr ADDR --before REGEX [--after REGEX]
tools/redisasm.py verify
```

`patch` decodes DB data into instructions; `data` is its **inverse** — it turns
mis-decoded instruction lines back into a labelled DB block (see Step 2c).

All commands operate on `source/zanac.asm` and `source/zanac.rom` (repo root).

## Protocol

### Step 1 — Checkpoint (once per session)

```
.venv/bin/python tools/redisasm.py checkpoint
```

Creates `source/zanac-NN.asm` (next available number).  Run this **once**
before the first patch in a session.  If `verify` fails later, the tool
reverts `source/zanac.asm` to this checkpoint automatically.

### Step 2 — Patch each DB region

```
.venv/bin/python tools/redisasm.py patch \
    --before "ANCHOR_BEFORE_REGEX" \
    --after  "ANCHOR_AFTER_REGEX"  \
    --start  0xADDR \
    --end    0xADDR
```

| Argument | Description |
|---|---|
| `--before REGEX` | Python regex that matches a line appearing **before** the DB block (e.g. the last instruction before the block, or the preceding label). |
| `--after REGEX`  | Python regex that matches the **first line after** the DB block (e.g. the label of the following routine). |
| `--start ADDR`   | ROM address of the **first byte to disassemble** (hex). May be greater than the block start — DB bytes before `--start` are automatically kept as DB lines. |
| `--end ADDR`     | ROM address of the **first byte NOT to disassemble** (exclusive). Bytes from `--end` to the anchor-after address are kept as DB lines. |

The tool:
1. Finds the DB slice by locating the first DB line after `--before` up to the
   line matching `--after`.
2. Reads all raw bytes from those DB lines.
3. Reads the block's starting ROM address from the first DB line's address
   comment; computes prefix = `--start` − block_start (kept as DB).
4. Computes the data suffix (`--end` to block end) from the remaining bytes.
5. Opens openMSX, loads the ROM, breaks at `0x402B` (both pages mapped).
6. Disassembles `--start` → `--end` via repeated `debug disasm` calls.
7. Replaces the DB slice with: prefix data DB lines + start label (if known) +
   instruction lines + suffix data DB lines.
8. Writes updated `source/zanac.asm`.

**Tip:** Use address comments as `--before` anchors for precision.  The last
instruction before a DB block has a known ROM address in its comment, so
`--before "; 0x453d"` is both unambiguous and self-documenting.

Repeat Step 2 for each region listed in `kb/guides/db-sections-with-code.md`.

### Step 2b — Add labels to already-decoded instructions

Some routines are already disassembled as Z80 instructions but have no label,
so calls to them appear as `; -> LAB_ram_XXXX` without a matching definition.
Use `add-label` to insert the label line — no openMSX required.

Because every instruction line in `source/zanac.asm` now ends with a ROM
address comment (e.g. `; 0x730b`), the primary form only needs the address:

```
.venv/bin/python tools/redisasm.py add-label --addr 0xADDR
```

The tool searches for the line whose address comment matches `--addr` and
inserts the label immediately before it.

Use the explicit `--before` form only when the address comment is absent or
ambiguous:

```
.venv/bin/python tools/redisasm.py add-label \
    --addr   0xADDR \
    --before "REGEX_MATCHING_FIRST_INSTRUCTION_OF_ROUTINE" \
    --after  "REGEX_NARROWING_SEARCH_WINDOW"
```

| Argument | Description |
|---|---|
| `--addr ADDR`    | ROM address of the routine entry. Label name comes from KB_LABELS if present; otherwise `LAB_ram_XXXX` is generated. |
| `--before REGEX` | (Optional) Python regex matching the first instruction line. Overrides the address-comment lookup. |
| `--after REGEX`  | (Optional, only with `--before`) Only search after the first line matching this regex. |

The command is idempotent: if the label already exists in the file it prints a
message and exits cleanly without modifying the file.

### Step 2c — Convert code back to DB (`data`)

The **inverse of `patch`**. When the disassembler greedily decoded a data table
as instructions, two things are wrong: the table shows as garbage instructions,
and — if the table's last byte decoded as a multi-byte opcode — it **absorbs the
leading byte of the routine that follows**, so that routine's entry is rendered
one byte short (e.g. a handler's `BIT 7,(IX+0)` = `DD CB 00 7E` loses its `DD`).
Such regions still assemble byte-identically, so `verify` passes; `data` fixes
the *rendering*.

```
.venv/bin/python tools/redisasm.py data \
    --before "ANCHOR_BEFORE_REGEX" \
    --after  "RESYNC_LINE_REGEX"   \
    --start  0xADDR   --end 0xADDR  \
    --label  optional_name
```

| Argument | Description |
|---|---|
| `--before REGEX` | Matches the line **immediately before** the data region (use its `; 0xADDR` comment). |
| `--after REGEX`  | Matches a line **after** the region whose decode is **already correct** — a re-sync point. It is preserved; everything between `--before` and it is replaced. |
| `--start ADDR`   | First data byte. |
| `--end ADDR`     | First byte **after** the data (exclusive) = the following routine's true entry. |
| `--label NAME`   | Optional label emitted before the `DB` block. |

The tool:
1. Reads the raw bytes for `[--start, --end)` straight from `zanac.rom` and emits
   them as `DB` lines (16/line, address-commented), preceded by `--label` if given.
2. Re-disassembles, via openMSX, any **absorbed entry bytes** `[--end, after_addr)`
   (and any code before `--start`), so the following routine's first instruction
   renders correctly again.
3. Splices the result over the replaced slice; the `--after` line and everything
   past it are untouched.

openMSX is only launched when there is code to re-disassemble (i.e. `--end <
after_addr`, the absorbed-entry case); a pure data run with `--end == after_addr`
is a fast file-only edit.

**Choosing `--after`:** pick the first line past the table whose address comment
is a true instruction boundary. The Z80 stream re-syncs within a few bytes, so a
`JR`/`CALL` shortly after the absorbed entry is usually already correct — use it.

Example (sprint 0053 — proto-box tables + absorbed box-handler entry at 0x7826):

```
.venv/bin/python tools/redisasm.py data \
    --before "; 0x77e9" --after "; 0x782a" \
    --start 0x77ea --end 0x7826 --label proto_box_type_table
# → DB 0x77ea–0x7825, then re-disasm BIT 7,(IX+0) at 0x7826
```

A contiguous data run can hold several KB sub-tables; emit one `--label` at its
start (the rest stay documented by address in the KB). The command **cannot**
split a run at an internal boundary — everything between `--end` and `--after`
must be code.

### Step 3 — Verify

```
.venv/bin/python tools/redisasm.py verify
```

Runs the full pipeline:

```
zanackb annotate source/zanac.asm -o build/zanac-annotated.asm
sjasmplus --raw=build/zanac-annotated.rom build/zanac-annotated.asm
diff build/zanac-annotated.rom source/zanac.rom  (byte-level)
```

- **Pass**: prints `ROM byte-identical ✓`.
- **Fail**: prints the first mismatch address, reverts `source/zanac.asm` to the
  last checkpoint, and exits with code 1.

## Finding anchor patterns

The `--before` and `--after` patterns are matched against ASM lines with
`re.search`, so they do not need to be full-line matches.

Good `--before` anchors (in order of preference):
- **ROM address comment of the last instruction before the DB block** — e.g.
  `--before "; 0x453d"`.  This is unambiguous and uses the address comments
  that every instruction line now carries.
- The `SUB_ram_XXXX:` or `LAB_ram_XXXX:` label of the routine immediately
  before the block.

Good `--after` anchor:
- The `SUB_ram_XXXX:` or `LAB_ram_XXXX:` label of the routine **immediately
  after** the DB block.

Example — finding anchors for a block starting at 0x4C8B:
1. Look up the ROM address of the instruction immediately before the block
   (0x4C8A): `--before "; 0x4c8a"`.
2. Grep for the next label: `grep -n "ram_4d" source/zanac.asm` → `SUB_ram_4da5:` → use as `--after`.

## Code vs data boundary

If the DB block contains a mix of code and trailing data (e.g. a lookup table
after the last `RET`), pass the code end as `--end` and the data bytes are
automatically kept as DB.

Use `openMSX` or byte inspection to locate the end of executable code:
- Look for the last `RET` / `RET NC` / `JP` with no fall-through.
- Bytes after that point that look like table values (small integers, address
  pairs, signed offsets) should remain as DB.

## Example session

```sh
# DB block at 0x4C8B–0x4DA4: code ends at 0x4CF6, data 0x4CF7–0x4DA4

.venv/bin/python tools/redisasm.py checkpoint

# --before uses the ROM address of the last instruction before the block
.venv/bin/python tools/redisasm.py patch \
    --before "; 0x4c8a" \
    --after  "SUB_ram_4da5:" \
    --start  0x4C8B \
    --end    0x4CF7

# Add labels for routines already decoded but lacking a definition
# Primary form: locate by ROM address comment — no --before needed
.venv/bin/python tools/redisasm.py add-label --addr 0x730B
.venv/bin/python tools/redisasm.py add-label --addr 0x7548

.venv/bin/python tools/redisasm.py verify
```

## KB label map

`tools/redisasm.py` maintains an internal `KB_LABELS` dictionary mapping ROM
addresses to canonical names.  When the disassembler encounters a known address
it emits a label line and annotates branch/call targets with `; -> name`.

To add a new label (e.g. for a newly identified function entry point), add a
line to `_KB_RAW` inside the script:

```
my_function 0xADDR
```

Labels for the three most recently decoded regions were added in this pass:

| Label | Address |
|---|---|
| `entity_post` | `0x44BA` |
| `player_pos_snapshot` | `0x4C8B` |
| `sub_4e7b` | `0x4E7B` (pre-existing) |
