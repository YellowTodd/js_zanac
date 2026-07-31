# Task: Map and decode DB sections

**Trigger:** Run this task after every 3–5 completed sprints, or whenever
`zanackb validate` shows a noticeable increase in "no KB entry" warnings for
addresses that haven't been located yet.

**Goal:** Find every contiguous `DB` block in `source/zanac.asm` that contains
live Z80 code, decode it with `redisasm.py patch`, and keep
`kb/guides/db-sections-with-code.md` accurate.

---

## Why this process exists

Ghidra emits `DB` (raw byte) directives for any region it cannot statically
trace — typically code reached via `JP HL`, ISR hooks, or indirect dispatch
tables. After each sprint we discover new call-targets inside those blocks.
Leaving them as `DB` blocks makes cross-references opaque, prevents label
propagation, and causes false "no KB entry" warnings that hide real gaps.

---

## Tooling

| Tool | Purpose |
|------|---------|
| `tools/map_db_sections.py` | Scans ASM + KB; reports addresses inside DB blocks |
| `tools/redisasm.py checkpoint` | Save ASM snapshot (once per session) |
| `tools/redisasm.py patch` | Replace a DB run with decoded instructions |
| `tools/redisasm.py add-label` | Insert a label before an already-decoded address |
| `tools/redisasm.py verify` | Assemble and confirm ROM byte-identity |
| `zanackb validate` | Check KB integrity (0 errors required before closing task) |

---

## Phase A — Map

**Run the cross-reference script:**

```bash
.venv/bin/python tools/map_db_sections.py
```

The script parses every `DB` line in `source/zanac.asm`, computes the exact
byte range from actual DB operand counts (not a heuristic), then cross-references
all KB-referenced addresses (from `calls:`, `called_by:`, and body text) against
those ranges.

**Output sections:**

- **`[CODE — called or jumped to]`**: addresses that appear in a `calls:` or
  `called_by:` frontmatter field of some KB file AND land inside a DB block.
  These are the primary targets for decoding.

- **`[DATA? — body mention only]`**: addresses referenced in free text only,
  possibly documented data tables (graphics, sound, level data). Usually safe
  to leave as `DB` — confirm before touching.

**Save the output for Phase B:**

```bash
.venv/bin/python tools/map_db_sections.py > /tmp/db_map.txt
```

---

## Phase B — Classify each CODE hit

For each address in the `[CODE]` section, answer two questions:

### B1. Is the reference really a CALL/JP (code), or a data read (false positive)?

Check the KB file that references the address:

```bash
grep -r "0xNNNN" kb/
```

If the KB says `calls: [0xNNNN]` but the body says "reads table at 0xNNNN" or
the address is a `LD HL, 0xNNNN` source, it is a data pointer — reclassify as
`data?` and skip decoding.

### B2. What are the block boundaries?

For the DB block reported by the script, read the ASM lines around it to find
anchor labels:

```python
Read("source/zanac.asm", offset=reported_first_line - 5, limit=10)
Read("source/zanac.asm", offset=reported_last_line, limit=5)
```

Record:
- `BEFORE`: a unique regex that matches the last decoded line BEFORE the DB block
- `AFTER`: a unique regex that matches the first decoded line or label AFTER the DB block
- `START`: exact start address of the DB block (from script output)
- `END`: exact end address of the DB block, exclusive (from script output — the
  second number in `0xSTART–0xEND`)

> **Note:** If `AFTER` is a label line (e.g. `SUB_ram_XXXX:`) use it directly.
> The `--after` regex must match uniquely within a narrow window.

### B3. Does the block straddle data?

If the DB block also contains known data (e.g., a credits text table followed by
code), inspect the raw bytes:

```python
data = bytes(msx.read_memory(block_start, block_size))
for i in range(0, block_size, 16):
    print(f"  {block_start+i:04X}: {' '.join(f'{b:02X}' for b in data[i:i+16])}")
```

Use `z80dasm` on a sub-range if needed to confirm instruction boundaries before
patching.

---

## Phase C — Patch each code block

### C0. Checkpoint (once per session)

```bash
.venv/bin/python tools/redisasm.py checkpoint
```

### C1. Patch

For each confirmed code block, in address order (low → high):

```bash
.venv/bin/python tools/redisasm.py patch \
    --before "BEFORE_REGEX" \
    --after  "AFTER_REGEX"  \
    --start  0xSTART --end 0xEND
```

Inspect the decoded instructions immediately after each patch:

```bash
# (Read the patched lines to confirm the disassembly looks correct)
```

If the patch produces obvious garbage (e.g., runs of `LD r,r` / `NOP` that do
not match any surrounding code patterns), the block may contain embedded data.
Split the patch into sub-ranges and retry.

### C2. Add entry-point labels

For each patched block, add a label for the primary entry address and any
secondary entry points that are called from outside the block:

```bash
# Primary entry — always add:
.venv/bin/python tools/redisasm.py add-label --addr 0xENTRY

# Secondary entries — add if referenced via CALL from outside the block:
.venv/bin/python tools/redisasm.py add-label --addr 0xSECONDARY
```

To find secondary entries: grep for `CALL.*0xNNNN` in the decoded area where
NNNN is in the block range:

```bash
grep -n "CALL.*0x8[bcde]\|CALL.*0x8f[0-5]" source/zanac.asm | grep -v "; 0x8"
```

(Adjust address range to match the block.)

---

## Phase D — ROM verification

After all patches in the session:

```bash
.venv/bin/python tools/redisasm.py verify
```

Must print `ROM byte-identical ✓`. If it fails, the patch introduced a mistake —
revert to the checkpoint:

```bash
cp source/zanac-04.asm source/zanac.asm   # use the checkpoint number printed at C0
```

---

## Phase E — KB validation

```bash
.venv/bin/zanackb validate
```

Must print `0 errors`. Warnings for missing KB entries are expected and tracked
separately. Fix any errors before proceeding.

---

## Phase F — Update `kb/guides/db-sections-with-code.md`

1. **Status summary table**: increment "Patched and ROM-verified" count; reset
   "Pending" to 0 if all hits resolved.

2. **All patched DB blocks table**: add one row per newly patched block:

   ```markdown
   | 0xSTART–0xEND | `entry_label` | One-line description of what the code does |
   ```

3. **Move entries from "Pending" to "Previously patched"**: mark each resolved
   block with ✓.

4. **Correct any stale documentation**: if a block previously described as "data"
   turned out to be code (or vice versa), update the description and add a
   correction note.

5. **Re-run the map script** and confirm output matches the updated guide:

   ```bash
   .venv/bin/python tools/map_db_sections.py
   ```

   If the `[CODE]` section is now empty, the guide is in sync.

---

## Decision rules for DATA blocks

Do NOT patch these as code:

| Pattern | Classification |
|---------|---------------|
| Referenced only in graphics-data.md or gfx_*.md | Graphics data |
| Referenced only in sound-engine.md or sound_track*.md | Sound/music data |
| Referenced only in scroll_*.md or level-data-format.md | Level/map data |
| Referenced only in keyboard-input.md with warp addresses | Warp lookup tables |
| Referenced only in entity_jump_table.md as a table address | Jump table data |
| Referenced in multiple sprints as "table at 0xNNNN" | Any data table |

These DB blocks are correct as-is; only add KB entries for the data structure if
it doesn't have one yet.

---

## Known DATA blocks (do not patch)

Confirmed data blocks that the map script will always report — expected, not
actionable:

| Block | Content |
|-------|---------|
| 0x4775–0x4897 | Credits script text (preceding entity_update) |
| 0x4CF7–0x4DA4 | Vertical collision distance table |
| 0x5236–0x5A10 | Sound track / instrument data |
| 0x5D2C–0x5EFB | Logo bitmap + color data |
| 0x5EFC–0x64D2 | Charset bitmap data |
| 0x64D3–0x666E | Charset color data |
| 0x666F–0x6704 | BG tile bitmap A |
| 0x6705–0x68A8 | BG tile bitmap B |
| 0x68A9–0x68DC | BG tile color A |
| 0x68DD–0x6975 | BG tile color B |
| 0x6976–0x70B6 | Sprite pattern data |
| 0x70B7–0x70EA | Entity jump table (handler addresses) |
| 0x9B64–0xBE26 | Level/map scroll data, spawn tables, sound cue lists |
| 0xBE76–0xBF2B | Spawn velocity and count tables |

---

## History

| Session | Blocks patched | Notes |
|---------|---------------|-------|
| After sprint 0030 | 0x453E–0x455F, 0x5D02–0x5D19, 0x8BF5–0x8F5D, 0xBF9C–0xBF9F | First full run of this process; also confirmed 0xBE27/0xBFAB were already decoded |
