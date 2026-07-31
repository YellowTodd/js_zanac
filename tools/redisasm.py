#!/usr/bin/env python3
"""
redisasm.py — Patch source/zanac.asm by selectively disassembling DB-block
code regions via openMSX.

Usage (from repo root) — run in order:

  # 1. Create a checkpoint (once per update session)
  tools/redisasm.py checkpoint

  # 2. Patch one DB block (repeat for each region in the guide)
  tools/redisasm.py patch \\
      --before REGEX --after REGEX \\
      --start ADDR --end ADDR

  # 3. Verify ROM byte-identity; reverts zanac.asm on mismatch
  tools/redisasm.py verify

ADDR: hex ROM address, e.g. 0x44BA.
REGEX: Python regex matched anywhere in an ASM line, e.g. "SUB_ram_4496:".
--start / --end: code range to disassemble (end is exclusive).
  DB bytes in the block before --start are not supported (error if present).
  DB bytes in the block after --end are kept as-is in DB lines.

openMSX must NOT be already running for the 'patch' command.
"""

from __future__ import annotations

import argparse
import re
import shutil
import subprocess
import sys
import time
from pathlib import Path

# ── paths ─────────────────────────────────────────────────────────────────────
ROOT = Path(__file__).resolve().parent.parent  # repo root
ROM = ROOT / "source" / "zanac.rom"
ASM = ROOT / "source" / "zanac.asm"
ROM_BASE = 0x4000
BREAK_ADDR = 0x402B  # after map_page2 + 0x513F, both ROM pages mapped

sys.path.insert(0, str(ROOT / "tools" / "zanackb"))
from openmsx import OpenMsxError, openmsx_session  # noqa: E402

# ── KB label map ──────────────────────────────────────────────────────────────
# address → canonical name used for branch-target annotations and start labels.
_KB_RAW = """
cold_start 0x4010
init_screen_mode 0x428A
init_vdp_regs 0x42BA
disable_display 0x42D7
enable_display 0x42E2
vdp_int_disable 0x42ED
vdp_int_enable 0x42F8
wait_one_frame 0x4306
read_options 0x4343
check_start_key 0x43D2
vblank_isr 0x43DA
entity_dispatch 0x445F
entity_post 0x44BA
collision_check 0x4560
entity_update 0x4898
sprite_shadow_push 0x48A9
entity_clear 0x48D0
Y_motion_sub 0x48DE
X_motion_sub 0x48F8
anim_sub 0x4912
Y_homing_sub 0x4942
X_homing_sub 0x496B
render_lives_score 0x4996
render_topscore_row2 0x49A7
render_score_row2 0x49AF
render_score_bcd 0x49B5
write_digit_to_vram 0x4B83
update_status_bar 0x4C4D
render_hiscore_digit 0x4C68
player_pos_snapshot 0x4C8B
update_fire_display 0x4DA5
map_page2 0x4E45
detect_slot 0x4E50
sub_4e7b 0x4E7B
reset_enemies_and_psg 0x516C
tile_to_vram_addr 0x5BDD
wait_frames 0x5BEC
vdp_write_byte_di 0x5BFC
vdp_set_addr_write 0x5C25
load_logo_tiles 0x5C3C
load_bg_tiles 0x5C60
load_charset_sprites 0x5CA5
decompress_block 0x5CCF
gfx_logo_bitmap 0x5D2C
gfx_logo_colors 0x5EF0
gfx_charset_bitmap 0x5EFC
gfx_charset_colors 0x64D3
gfx_bg_late_bitmap_a 0x666F
gfx_bg_late_bitmap_b 0x6705
gfx_bg_late_colors_a 0x68A9
gfx_bg_late_colors_b 0x68DD
gfx_sprite_patterns 0x6976
entity_jump_table 0x70B7
scroll_map_reader 0x9888
scroll_vram_write 0x9A79
scroll_sync 0x9AE4
"""

KB_LABELS: dict[int, str] = {}
for _line in _KB_RAW.strip().splitlines():
    _name, _addr = _line.split()
    KB_LABELS[int(_addr, 16)] = _name

# ── openMSX disasm → zanac.asm format ─────────────────────────────────────────
_REGS = {
    "af'",
    "af",
    "bc",
    "de",
    "hl",
    "sp",
    "ix",
    "iy",
    "ixh",
    "ixl",
    "iyh",
    "iyl",
    "a",
    "b",
    "c",
    "d",
    "e",
    "f",
    "h",
    "l",
    "i",
    "r",
}
_COND = {"nz", "z", "nc", "po", "pe", "p", "m"}
_UPPER_TOKENS = _REGS | _COND | {"c"}

_HEX_RE = re.compile(r"#([0-9A-Fa-f]+)")
_TOKEN_RE = re.compile(r"([,\s()+\-/*]+)")


def _fmt_operands(raw: str) -> str:
    s = _HEX_RE.sub(lambda m: "0x" + m.group(1).lower(), raw)
    s = re.sub(r",(?!\s)", ", ", s)
    parts = _TOKEN_RE.split(s)
    return "".join(
        part.upper() if part.lower() in _UPPER_TOKENS else part for part in parts
    )


def _parse_disasm(raw: str) -> tuple[str, str, int]:
    raw = raw.strip("'")
    m = re.match(r"\{(.+?)\s*\}\s*([0-9A-F ]+)$", raw)
    if not m:
        raise ValueError(f"Cannot parse disasm reply: {raw!r}")
    instr = m.group(1).strip()
    byte_count = len(m.group(2).strip().split())
    parts = instr.split(None, 1)
    mnemonic = parts[0].upper()
    operands = _fmt_operands(parts[1]) if len(parts) > 1 else ""
    return mnemonic, operands, byte_count


def _find_branch_target(mnemonic: str, operands: str) -> int | None:
    if mnemonic not in {
        "CALL",
        "JP",
        "JR",
        "DJNZ",
        "CALL NZ",
        "CALL Z",
        "CALL NC",
        "CALL C",
        "JP NZ",
        "JP Z",
        "JP NC",
        "JP C",
        "JP PO",
        "JP PE",
        "JP P",
        "JP M",
        "JR NZ",
        "JR Z",
        "JR NC",
        "JR C",
    }:
        return None
    tok = operands.rstrip().rstrip(",").rsplit(",", 1)[-1].strip()
    if tok.startswith("0x"):
        try:
            return int(tok, 16)
        except ValueError:
            pass
    return None


def _format_line(
    mnemonic: str, operands: str, addr: int, label_map: dict[int, str]
) -> str:
    INDENT = "        "
    MNE_W = 9
    COMM_COL = 68

    body = f"{INDENT}{mnemonic:<{MNE_W}}{operands}"
    target = _find_branch_target(mnemonic, operands)
    if target is not None:
        tname = label_map.get(target) or f"LAB_ram_{target:04x}"
        comment = f"; 0x{addr:04x}  -> {tname}"
    else:
        comment = f"; 0x{addr:04x}"

    return f"{body:<{COMM_COL}} {comment}"


def disasm_region(
    client, start: int, end: int, all_labels: dict[int, str]
) -> list[str]:
    """Disassemble ROM addresses [start, end) via openMSX.

    Inserts a label line before each address (other than start) that
    appears in all_labels.
    """
    out: list[str] = []
    addr = start
    while addr < end:
        raw = client.cmd(f"debug disasm {addr}")
        try:
            mnemonic, operands, nbytes = _parse_disasm(raw)
        except ValueError as exc:
            print(f"  WARNING at 0x{addr:04X}: {exc}; emitting DB", file=sys.stderr)
            b = ROM.read_bytes()[addr - ROM_BASE]
            out.append(f"        DB       0x{b:02x}")
            addr += 1
            continue

        if addr != start and addr in all_labels:
            out.append(f"{all_labels[addr]}:")

        out.append(_format_line(mnemonic, operands, addr, all_labels))
        addr += nbytes

    return out


# ── DB helpers ────────────────────────────────────────────────────────────────
_DB_LINE_RE = re.compile(r"^\s+DB\s+(.+)")


def _parse_db_hex(line: str) -> list[int]:
    m = _DB_LINE_RE.match(line)
    if not m:
        return []
    content = m.group(1).split(";")[0]  # strip trailing address comment
    return [int(tok.strip(), 16) for tok in content.split(",") if tok.strip()]


def get_db_bytes(asm_lines: list[str], start: int, end: int) -> bytes:
    """Extract all raw bytes declared by DB lines in asm_lines[start:end]."""
    result: list[int] = []
    for line in asm_lines[start:end]:
        result.extend(_parse_db_hex(line))
    return bytes(result)


def emit_db_lines(data: bytes, base_addr: int | None = None) -> list[str]:
    """Format raw bytes as 16-per-line DB source lines."""
    COMM_COL = 68
    lines = []
    for i in range(0, len(data), 16):
        chunk = data[i : i + 16]
        body = "        DB       " + ", ".join(f"0x{b:02x}" for b in chunk)
        if base_addr is not None:
            body = f"{body:<{COMM_COL}} ; 0x{base_addr + i:04x}"
        lines.append(body)
    return lines


# ── anchor search ─────────────────────────────────────────────────────────────


def find_db_slice(
    asm_lines: list[str], anchor_before_re: str, anchor_after_re: str
) -> tuple[int, int]:
    """Return ``(first_db_line_idx, anchor_after_idx)``.

    Searches for anchor_before first, then the first DB line after it,
    then anchor_after from that DB line onward.
    """
    before_re = re.compile(anchor_before_re)
    after_re = re.compile(anchor_after_re)
    db_re = re.compile(r"^\s+DB\s+")

    before_idx = next((i for i, l in enumerate(asm_lines) if before_re.search(l)), None)
    if before_idx is None:
        raise LookupError(f"anchor_before not found: {anchor_before_re!r}")

    start_idx = next(
        (i for i in range(before_idx + 1, len(asm_lines)) if db_re.match(asm_lines[i])),
        None,
    )
    if start_idx is None:
        raise LookupError(f"No DB line after anchor_before {anchor_before_re!r}")

    end_idx = next(
        (i for i in range(start_idx, len(asm_lines)) if after_re.search(asm_lines[i])),
        None,
    )
    if end_idx is None:
        raise LookupError(f"anchor_after not found: {anchor_after_re!r}")

    return start_idx, end_idx


# ── checkpoint / revert ───────────────────────────────────────────────────────


def latest_checkpoint() -> Path | None:
    i = 0
    last: Path | None = None
    while True:
        p = ASM.with_name(f"{ASM.stem}-{i:02d}{ASM.suffix}")
        if not p.exists():
            break
        last = p
        i += 1
    return last


def cmd_checkpoint(_args) -> None:
    i = 0
    while True:
        dst = ASM.with_name(f"{ASM.stem}-{i:02d}{ASM.suffix}")
        if not dst.exists():
            shutil.copy2(ASM, dst)
            print(f"Checkpoint: {dst.name}")
            return
        i += 1


# ── verify ────────────────────────────────────────────────────────────────────


def run_verify() -> bool:
    """Run zanackb annotate → sjasmplus → byte-compare.  Return True on match."""
    zanackb_bin = Path(sys.executable).parent / "zanackb"
    ann_asm = ROOT / "build" / "zanac-annotated.asm"
    ann_rom = ROOT / "build" / "zanac-annotated.rom"

    print("\nVerifying ROM …")

    r = subprocess.run(
        [str(zanackb_bin), "annotate", str(ASM), "-o", str(ann_asm)],
        capture_output=True,
        text=True,
    )
    if r.returncode != 0:
        print(f"  zanackb annotate FAILED:\n{r.stderr}", file=sys.stderr)
        return False
    print(f"  annotated  → {ann_asm.relative_to(ROOT)}")

    r = subprocess.run(
        ["sjasmplus", f"--raw={ann_rom}", str(ann_asm)],
        capture_output=True,
        text=True,
    )
    if r.returncode != 0:
        print(f"  sjasmplus FAILED:\n{r.stderr}", file=sys.stderr)
        return False
    print(f"  assembled  → {ann_rom.relative_to(ROOT)}")

    orig = ROM.read_bytes()
    built = ann_rom.read_bytes()
    if orig == built:
        print("  ROM byte-identical ✓")
        return True

    for i, (a, b) in enumerate(zip(orig, built)):
        if a != b:
            print(
                f"  MISMATCH at file offset 0x{i:04X} "
                f"(ROM addr 0x{i + ROM_BASE:04X}): "
                f"expected 0x{a:02X}, got 0x{b:02X}",
                file=sys.stderr,
            )
            break
    if len(orig) != len(built):
        print(
            f"  size mismatch: {len(orig)} B vs {len(built)} B",
            file=sys.stderr,
        )
    return False


def cmd_verify(_args) -> None:
    if not run_verify():
        cp = latest_checkpoint()
        if cp:
            shutil.copy2(cp, ASM)
            print(f"Reverted to {cp.name}")
        else:
            print("No checkpoint found; zanac.asm NOT reverted.", file=sys.stderr)
        sys.exit(1)


# ── add-label ─────────────────────────────────────────────────────────────────


def cmd_add_label(args) -> None:
    addr = args.addr
    label = KB_LABELS.get(addr, f"LAB_ram_{addr:04x}")

    asm_lines = ASM.read_text(encoding="utf-8").splitlines(keepends=True)

    label_line = f"{label}:\n"
    if any(l == label_line or l.rstrip("\n") == f"{label}:" for l in asm_lines):
        print(f"Label {label!r} already present in {ASM.name}; skipping.")
        return

    if args.before:
        # Explicit regex: search (optionally after --after window) for the line.
        search_start = 0
        if args.after:
            after_re = re.compile(args.after)
            idx = next((i for i, l in enumerate(asm_lines) if after_re.search(l)), None)
            if idx is None:
                print(
                    f"ERROR: --after pattern not found: {args.after!r}", file=sys.stderr
                )
                sys.exit(1)
            search_start = idx + 1
        before_re = re.compile(args.before)
        insert_at = next(
            (
                i
                for i in range(search_start, len(asm_lines))
                if before_re.search(asm_lines[i])
            ),
            None,
        )
        if insert_at is None:
            print(
                f"ERROR: --before pattern not found: {args.before!r}", file=sys.stderr
            )
            sys.exit(1)
    else:
        # Primary: find instruction by its ROM address comment ("; 0xADDR").
        addr_re = re.compile(r";\s*0x{:04x}(\s|$)".format(addr))
        insert_at = next(
            (i for i, l in enumerate(asm_lines) if addr_re.search(l)),
            None,
        )
        if insert_at is None:
            print(
                f"ERROR: no instruction with address comment 0x{addr:04x} found; "
                f"use --before to specify insertion point",
                file=sys.stderr,
            )
            sys.exit(1)

    new_lines = list(asm_lines)
    new_lines.insert(insert_at, label_line)
    ASM.write_text("".join(new_lines), encoding="utf-8")
    print(
        f"Inserted  {label}:  before line {insert_at + 1}  ({ASM.name} now {len(new_lines)} lines)"
    )


# ── patch ─────────────────────────────────────────────────────────────────────


def cmd_patch(args) -> None:
    code_start = args.start
    code_end = args.end

    asm_lines = ASM.read_text(encoding="utf-8").splitlines(keepends=True)

    # Build label map: KB_LABELS merged with auto-generated labels from ASM.
    asm_label_re = re.compile(r"^(SUB_ram_|LAB_ram_)([0-9A-Fa-f]+):")
    all_labels: dict[int, str] = dict(KB_LABELS)
    for line in asm_lines:
        m = asm_label_re.match(line)
        if m:
            addr = int(m.group(2), 16)
            if addr not in all_labels:
                all_labels[addr] = m.group(1) + m.group(2)

    try:
        db_start, db_end = find_db_slice(asm_lines, args.before, args.after)
    except LookupError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        sys.exit(1)

    # Read all bytes currently in the DB block.
    block_bytes = get_db_bytes(asm_lines, db_start, db_end)
    block_size = len(block_bytes)
    code_size = code_end - code_start

    # Determine block's starting ROM address from the first DB line's address comment.
    first_db = asm_lines[db_start]
    addr_m = re.search(r";\s*(0x[0-9a-fA-F]+)", first_db)
    block_start_addr = int(addr_m.group(1), 16) if addr_m else code_start
    prefix_size = code_start - block_start_addr

    if prefix_size < 0:
        print(
            f"ERROR: --start 0x{code_start:04X} is before DB block start "
            f"0x{block_start_addr:04X}",
            file=sys.stderr,
        )
        sys.exit(1)
    if prefix_size + code_size > block_size:
        print(
            f"ERROR: code range 0x{code_start:04X}–0x{code_end - 1:04X} "
            f"({code_size} bytes) + prefix ({prefix_size} bytes) exceeds "
            f"DB block ({block_size} bytes)",
            file=sys.stderr,
        )
        sys.exit(1)

    prefix_bytes = block_bytes[:prefix_size]
    suffix_bytes = block_bytes[prefix_size + code_size :]
    suffix_size = len(suffix_bytes)

    print(f"DB slice: ASM lines {db_start + 1}–{db_end} ({block_size} bytes)")
    if prefix_size:
        print(
            f"  data  0x{block_start_addr:04X}–0x{code_start - 1:04X}"
            f" ({prefix_size} bytes → kept as DB)"
        )
    print(f"  code  0x{code_start:04X}–0x{code_end - 1:04X} ({code_size} bytes)")
    if suffix_size:
        block_end_addr = code_end + suffix_size
        print(
            f"  data  0x{code_end:04X}–0x{block_end_addr - 1:04X}"
            f" ({suffix_size} bytes → kept as DB)"
        )

    # ── openMSX disassembly ──────────────────────────────────────────────────
    print(f"Launching openMSX, breaking at 0x{BREAK_ADDR:04X} …")
    with openmsx_session(rom=ROM) as client:
        client.power_on()
        client.cmd(f"set ::hit_{BREAK_ADDR:04x} 0")
        client.cmd(
            f"debug set_bp 0x{BREAK_ADDR:04X} true "
            f"{{set ::hit_{BREAK_ADDR:04x} 1; debug break}}"
        )
        client.cont()
        time.sleep(4)
        hit = client.cmd(f"set ::hit_{BREAK_ADDR:04x}")
        pc = int(client.cmd("reg PC"))
        if hit != "1" or pc != BREAK_ADDR:
            print(
                f"  WARNING: expected PC=0x{BREAK_ADDR:04X}, got 0x{pc:04X}",
                file=sys.stderr,
            )
        else:
            print(f"  Stopped at PC=0x{pc:04X}")

        print(
            f"  Disassembling 0x{code_start:04X}→0x{code_end - 1:04X} …",
            end=" ",
            flush=True,
        )
        code_lines = disasm_region(client, code_start, code_end, all_labels)
        print(f"{len(code_lines)} lines")

    # ── build replacement ────────────────────────────────────────────────────
    replacement: list[str] = []

    # Emit any leading data (before code_start) as DB lines.
    if prefix_bytes:
        replacement.extend(emit_db_lines(prefix_bytes, block_start_addr))

    # Emit start label if the address is known.
    if code_start in all_labels:
        replacement.append(f"{all_labels[code_start]}:")

    replacement.extend(code_lines)

    # Emit any trailing data as DB lines.
    if suffix_bytes:
        replacement.extend(emit_db_lines(suffix_bytes, code_end))

    # ── splice and write ─────────────────────────────────────────────────────
    new_lines = list(asm_lines)
    new_lines[db_start:db_end] = [l + "\n" for l in replacement]
    delta = len(replacement) - (db_end - db_start)
    print(
        f"  Replaced {db_end - db_start} DB lines with "
        f"{len(replacement)} lines (delta {delta:+d})"
    )

    ASM.write_text("".join(new_lines), encoding="utf-8")
    print(f"Patched {ASM.name}  ({len(new_lines)} lines total)")


# ── data (reverse of patch: code → DB) ─────────────────────────────────────────


def _addr_of(line: str) -> int | None:
    """Parse the ROM address from a line's ``; 0xADDR`` comment."""
    m = re.search(r";\s*(0x[0-9a-fA-F]+)", line)
    return int(m.group(1), 16) if m else None


def cmd_data(args) -> None:
    """Inverse of ``patch``: convert mis-decoded *instruction* lines back to DB.

    Marks ``[--start, --end)`` as DB data and re-disassembles any code that the
    greedy data decode straddled — bytes before ``--start`` and, importantly, the
    bytes after ``--end`` whose leading opcode byte the previous (data) decode
    absorbed — so the following routine entry decodes correctly again.

    ``--before`` / ``--after`` bound the slice of existing lines to replace;
    ``--after`` must match a line whose decode is already correct (a clean
    re-sync point), and is itself preserved.
    """
    data_start, data_end = args.start, args.end
    if data_end <= data_start:
        print("ERROR: --end must be greater than --start", file=sys.stderr)
        sys.exit(1)

    asm_lines = ASM.read_text(encoding="utf-8").splitlines(keepends=True)

    # Label map (KB + auto-detected) for the re-disassembled code parts.
    asm_label_re = re.compile(r"^(SUB_ram_|LAB_ram_)([0-9A-Fa-f]+):")
    all_labels: dict[int, str] = dict(KB_LABELS)
    for line in asm_lines:
        m = asm_label_re.match(line)
        if m:
            all_labels.setdefault(int(m.group(2), 16), m.group(1) + m.group(2))

    before_re = re.compile(args.before)
    after_re = re.compile(args.after)
    before_idx = next((i for i, l in enumerate(asm_lines) if before_re.search(l)), None)
    if before_idx is None:
        print(f"ERROR: --before not found: {args.before!r}", file=sys.stderr)
        sys.exit(1)
    slice_start = before_idx + 1
    after_idx = next(
        (i for i in range(slice_start, len(asm_lines)) if after_re.search(asm_lines[i])),
        None,
    )
    if after_idx is None or after_idx <= slice_start:
        print(f"ERROR: --after not found after --before: {args.after!r}", file=sys.stderr)
        sys.exit(1)

    slice_addrs = [
        a for a in (_addr_of(l) for l in asm_lines[slice_start:after_idx]) if a is not None
    ]
    after_addr = _addr_of(asm_lines[after_idx])
    if not slice_addrs or after_addr is None:
        print("ERROR: slice or --after line lacks an address comment", file=sys.stderr)
        sys.exit(1)
    slice_start_addr = slice_addrs[0]

    if not (slice_start_addr <= data_start < data_end <= after_addr):
        print(
            f"ERROR: need slice_start(0x{slice_start_addr:04X}) <= --start"
            f"(0x{data_start:04X}) < --end(0x{data_end:04X}) <= after(0x{after_addr:04X})",
            file=sys.stderr,
        )
        sys.exit(1)

    rom = ROM.read_bytes()
    need_pre = data_start > slice_start_addr
    need_suf = data_end < after_addr

    print(
        f"Code→DB slice: ASM lines {slice_start + 1}–{after_idx} "
        f"(0x{slice_start_addr:04X}–0x{after_addr - 1:04X})"
    )
    if need_pre:
        print(f"  code  0x{slice_start_addr:04X}–0x{data_start - 1:04X} (re-disasm)")
    print(f"  data  0x{data_start:04X}–0x{data_end - 1:04X} ({data_end - data_start} bytes → DB)")
    if need_suf:
        print(f"  code  0x{data_end:04X}–0x{after_addr - 1:04X} (re-disasm, absorbed entry)")

    pre_lines: list[str] = []
    suf_lines: list[str] = []
    if need_pre or need_suf:
        print(f"Launching openMSX, breaking at 0x{BREAK_ADDR:04X} …")
        with openmsx_session(rom=ROM) as client:
            client.power_on()
            client.cmd(f"set ::hit_{BREAK_ADDR:04x} 0")
            client.cmd(
                f"debug set_bp 0x{BREAK_ADDR:04X} true "
                f"{{set ::hit_{BREAK_ADDR:04x} 1; debug break}}"
            )
            client.cont()
            time.sleep(4)
            pc = int(client.cmd("reg PC"))
            print(
                f"  Stopped at PC=0x{pc:04X}"
                + ("" if pc == BREAK_ADDR else f"  (expected 0x{BREAK_ADDR:04X})")
            )
            if need_pre:
                pre_lines = disasm_region(client, slice_start_addr, data_start, all_labels)
            if need_suf:
                suf_lines = disasm_region(client, data_end, after_addr, all_labels)

    replacement: list[str] = list(pre_lines)
    if args.label:
        replacement.append(f"{args.label}:")
    replacement.extend(emit_db_lines(rom[data_start - ROM_BASE : data_end - ROM_BASE], data_start))
    replacement.extend(suf_lines)

    new_lines = list(asm_lines)
    new_lines[slice_start:after_idx] = [l + "\n" for l in replacement]
    print(
        f"  Replaced {after_idx - slice_start} lines with {len(replacement)} "
        f"lines (delta {len(replacement) - (after_idx - slice_start):+d})"
    )
    ASM.write_text("".join(new_lines), encoding="utf-8")
    print(f"Patched {ASM.name}  ({len(new_lines)} lines total)")


# ── CLI ───────────────────────────────────────────────────────────────────────


def _parse_addr(s: str) -> int:
    return int(s, 16)


def main(argv: list[str]) -> None:
    p = argparse.ArgumentParser(
        description="Selectively disassemble DB-block code regions in zanac.asm.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__.split("openMSX")[0].rstrip(),
    )
    sub = p.add_subparsers(dest="cmd", required=True)

    sub.add_parser(
        "checkpoint",
        help="Save current source/zanac.asm as source/zanac-NN.asm.",
    )

    pp = sub.add_parser(
        "patch",
        help="Disassemble one DB region and patch zanac.asm in place.",
    )
    pp.add_argument(
        "--before",
        required=True,
        metavar="REGEX",
        help="Regex matching a line anywhere before the DB block.",
    )
    pp.add_argument(
        "--after",
        required=True,
        metavar="REGEX",
        help="Regex matching the first line after the DB block.",
    )
    pp.add_argument(
        "--start",
        required=True,
        type=_parse_addr,
        metavar="ADDR",
        help="ROM address of first byte to disassemble (hex, must equal block start).",
    )
    pp.add_argument(
        "--end",
        required=True,
        type=_parse_addr,
        metavar="ADDR",
        help="ROM address of first byte NOT to disassemble (exclusive). "
        "Remaining bytes in the block are kept as DB.",
    )

    dp = sub.add_parser(
        "data",
        help="Inverse of patch: convert mis-decoded instruction lines to DB data, "
        "re-disassembling any absorbed routine entry after --end.",
    )
    dp.add_argument(
        "--before",
        required=True,
        metavar="REGEX",
        help="Regex matching the line just before the data region.",
    )
    dp.add_argument(
        "--after",
        required=True,
        metavar="REGEX",
        help="Regex matching a correctly-decoded line after the region (a re-sync "
        "point); it is preserved.",
    )
    dp.add_argument(
        "--start", required=True, type=_parse_addr, metavar="ADDR",
        help="ROM address of first data byte (hex).",
    )
    dp.add_argument(
        "--end", required=True, type=_parse_addr, metavar="ADDR",
        help="ROM address of first byte after the data (exclusive, hex).",
    )
    dp.add_argument(
        "--label", default=None, metavar="NAME",
        help="Optional label emitted before the DB block.",
    )

    al = sub.add_parser(
        "add-label",
        help="Insert a label line before the first ASM line matching --before.",
    )
    al.add_argument(
        "--addr",
        required=True,
        type=_parse_addr,
        metavar="ADDR",
        help="ROM address; derives label from KB_LABELS or as LAB_ram_XXXX.",
    )
    al.add_argument(
        "--before",
        default=None,
        metavar="REGEX",
        help="Insert label before the first line matching this regex. "
        "If omitted, the label is inserted before the instruction whose "
        "ROM address comment matches --addr.",
    )
    al.add_argument(
        "--after",
        default=None,
        metavar="REGEX",
        help="Only search for --before after the first line matching this regex "
        "(ignored when --before is omitted).",
    )

    sub.add_parser(
        "verify",
        help="Annotate + assemble + byte-compare ROM; revert zanac.asm on mismatch.",
    )

    args = p.parse_args(argv)
    dispatch = {
        "checkpoint": cmd_checkpoint,
        "add-label": cmd_add_label,
        "patch": cmd_patch,
        "data": cmd_data,
        "verify": cmd_verify,
    }
    dispatch[args.cmd](args)


if __name__ == "__main__":
    main(sys.argv[1:])
