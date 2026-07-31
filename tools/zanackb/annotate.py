"""Produce a fully commented copy of the raw disassembly.

The annotator does NOT parse Z80. It treats the disassembler's output as the
spine and injects comments by matching addresses on each line.

Addresses are detected by three strategies:
  1. Listing format       "4123:  CD A0 40   call 0x40A0"
  2. Address-in-comment   "    call 0x40A0    ; 0x4123"
  3. Label with hex name  "SUB_ram_41db:" / "LAB_ram_4042:" / "sub_4e7b:"
     + KB name fallback   "vblank_isr:" looked up by name in the KB
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

from .parser import KB, SymbolEntry

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

CONFIDENCE_ORDER = ["confirmed", "likely", "hypothesis", "guess"]

# Dividers emitted when the address crosses into a new region (feature E).
ROM_REGIONS: list[tuple[int, str]] = [
    (0x0000, "BIOS / Vectors (0x0000-0x3FFF)"),
    (0x4000, "ROM  0x4000 — Init / Bootstrap / Gameplay utilities"),
    (0x8000, "ROM  0x8000 — Enemy handlers / Scroll engine"),
    (0xA000, "ROM  0xA000 — Music & SFX data"),
    (0xC000, "RAM  0xC000 — Work RAM"),
    (0xE000, "RAM  0xE000 — Entity / Sprite state (game RAM)"),
    (0xF000, "RAM  0xF000 — Stack / System variables"),
]

DATA_DIRECTIVES = frozenset(["DB", "DW", "DS", "DEFB", "DEFW", "DEFS"])

# ---------------------------------------------------------------------------
# Regex patterns
# ---------------------------------------------------------------------------

ADDRESS_PATTERNS: list[re.Pattern[str]] = [
    re.compile(r"^\s*([0-9A-Fa-f]{4})[:\s]"),
    re.compile(r";\s*0x([0-9A-Fa-f]{4})\b"),
]
_LABEL_LINE_RE = re.compile(r"^(\w+):(?:\s|$)")
_LABEL_HEX_SUFFIX_RE = re.compile(r"_([0-9A-Fa-f]{4,5})$")
# Matches "; -> LABEL" comment — groups: ("; -> ", "LABEL")
_CALL_COMMENT_RE = re.compile(r"(;\s*->\s*)(\w+)")
# Matches a CALL/JP/JR with a hex operand — groups: (mnemonic, address_hex)
_CALL_INSTR_RE = re.compile(
    r"^\s+(CALL|JP|JR)\b[^;]*\b0x([0-9A-Fa-f]{4})\b", re.IGNORECASE
)
_DATA_LINE_RE = re.compile(r"^\s+(DB|DW|DS|DEFB|DEFW|DEFS)\b", re.IGNORECASE)
_CODE_LINE_RE = re.compile(r"^\s+\w")


# ---------------------------------------------------------------------------
# Address extraction helpers
# ---------------------------------------------------------------------------


def _addr_from_label(label: str) -> int | None:
    m = _LABEL_HEX_SUFFIX_RE.search(label)
    return int(m.group(1), 16) if m else None


def line_address(
    line: str,
    by_name: dict[str, SymbolEntry] | None = None,
) -> int | None:
    """Return the Z80 address associated with *line*, or None."""
    for pat in ADDRESS_PATTERNS:
        m = pat.search(line)
        if m:
            return int(m.group(1), 16)
    # Strategy 3: label line with hex address in name
    m = _LABEL_LINE_RE.match(line)
    if m:
        label = m.group(1)
        addr = _addr_from_label(label)
        if addr is not None:
            return addr
        if by_name is not None:
            entry = by_name.get(label)
            if entry is not None:
                return entry.address
    return None


# ---------------------------------------------------------------------------
# KB-path helper
# ---------------------------------------------------------------------------


def _kb_rel_path(source_path: Path | None) -> str | None:
    if source_path is None:
        return None
    parts = source_path.parts
    for i, p in enumerate(parts):
        if p == "kb":
            return "/".join(parts[i:])
    return str(source_path)


# ---------------------------------------------------------------------------
# Summary extraction
# ---------------------------------------------------------------------------


def _summary_section(body: str) -> str:
    """Return the first paragraph of the ## Summary section (or first body paragraph)."""
    in_summary = False
    out: list[str] = []
    for raw in body.splitlines():
        line = raw.rstrip()
        if re.match(r"^##\s+Summary", line):
            in_summary = True
            continue
        if in_summary:
            if line.startswith("#"):
                break
            if not line.strip() and not out:
                continue  # skip leading blanks
            if line.strip():
                out.append(line)
            else:
                break  # first blank line ends the paragraph
    if out:
        return "\n".join(out)
    # Fallback: first paragraph after the H1
    started = False
    out = []
    for raw in body.splitlines():
        line = raw.rstrip()
        if not started:
            if line.startswith("# ") or not line.strip():
                continue
            started = True
        if not line.strip() or line.startswith("#"):
            break
        out.append(line)
    return "\n".join(out)


# ---------------------------------------------------------------------------
# Reference formatting
# ---------------------------------------------------------------------------


def _fmt_ref(ref: int | str, kb: KB | None = None) -> str:
    if isinstance(ref, int):
        if kb:
            e = kb.by_address.get(ref)
            if e:
                return f"{e.name}(0x{ref:04X})"
        return f"0x{ref:04X}"
    return ref


# ---------------------------------------------------------------------------
# Header block (banner emitted before each KB entry's first instruction)
# ---------------------------------------------------------------------------


def _header_block(e: SymbolEntry, kb: KB | None = None) -> list[str]:
    bar = "; " + "=" * 70
    lines = [
        "",
        bar,
        f"; {e.name}   @ {e.addr_hex}"
        + (f"-{e.end_hex}" if e.end_hex else "")
        + f"   [{e.kind}, {e.confidence}]",
    ]
    lines.append(";")
    if e.tags:
        lines.append(f"; tags:     {', '.join(e.tags)}")
    if e.inputs:
        ins = ", ".join(f"{k}={v}" for k, v in e.inputs.items())
        lines.append(f"; in:       {ins}")
    if e.outputs:
        outs = ", ".join(f"{k}={v}" for k, v in e.outputs.items())
        lines.append(f"; out:      {outs}")
    if e.clobbers:
        lines.append(f"; clobs:    {', '.join(e.clobbers)}")
    if e.calls:
        lines.append(f"; calls:    {', '.join(_fmt_ref(r, kb) for r in e.calls)}")
    if e.called_by:
        lines.append(f"; calledby: {', '.join(_fmt_ref(r, kb) for r in e.called_by)}")
    lines.append(f"; sprint:   {e.sprint}")
    kb_path = _kb_rel_path(e.source_path)
    if kb_path:
        lines.append(f"; path:     {kb_path}")
    summary = _summary_section(e.body)
    if summary:
        lines.append(";")
        for ln in summary.splitlines():
            lines.append(f"; {ln}".rstrip())
    lines.append(bar)
    return lines


# ---------------------------------------------------------------------------
# Region dividers (feature E)
# ---------------------------------------------------------------------------


def _region_for(addr: int) -> tuple[int, str] | None:
    best: tuple[int, str] | None = None
    for start, name in ROM_REGIONS:
        if addr >= start:
            best = (start, name)
        else:
            break
    return best


def _region_divider(name: str) -> list[str]:
    bar = "; " + "#" * 70
    return ["", bar, f"; {name}", bar, ""]


# ---------------------------------------------------------------------------
# Call-comment resolution (features A & B)
# ---------------------------------------------------------------------------


def _resolve_call_comments(line: str, kb: KB) -> str:
    """Replace `; -> LABEL` with the KB name and confidence (or ⚠ UNKNOWN)."""

    def _repl(m: re.Match[str]) -> str:
        prefix = m.group(1)  # "; -> "
        label = m.group(2)  # e.g. "SUB_ram_516c"
        # Try address from label hex suffix
        addr = _addr_from_label(label)
        if addr is not None:
            entry = kb.by_address.get(addr)
            if entry:
                return f"{prefix}{entry.name} [{entry.confidence}]"
            if label.startswith("LAB"):  # skip simple labels
                return ""
            return f"{prefix}{label} [⚠ UNKNOWN 0x{addr:04X}]"
        # Try KB name lookup (for plain labels like "vblank_isr")
        entry = kb.by_name.get(label)
        if entry:
            return f"{prefix}{entry.name} [{entry.confidence}]"
        return f"{prefix}{label} [⚠ UNKNOWN]"

    return _CALL_COMMENT_RE.sub(_repl, line)


# ---------------------------------------------------------------------------
# Inline CALL/JP annotation (feature F)
# ---------------------------------------------------------------------------


def _inline_annotation(line: str, kb: KB) -> str:
    """For CALL/JP/JR lines without an existing `; ->` comment, append `; (name)`."""
    if "; ->" in line:
        return line
    m = _CALL_INSTR_RE.match(line)
    if not m:
        return line
    addr = int(m.group(2), 16)
    entry = kb.by_address.get(addr)
    if entry:
        return line.rstrip() + f"    ; ({entry.name})"
    return line


# ---------------------------------------------------------------------------
# Main annotate loop
# ---------------------------------------------------------------------------


@dataclass
class AnnotateStats:
    lines_in: int = 0
    lines_out: int = 0
    headers_emitted: int = 0
    inline_annotations: int = 0


def annotate(
    source_lines: Iterable[str],
    kb: KB,
    min_confidence: str | None = None,
) -> tuple[list[str], AnnotateStats]:
    """Return (annotated_lines, stats).

    `min_confidence` is one of 'confirmed', 'likely', 'hypothesis', 'guess'
    (or None = emit all). Headers are suppressed for entries whose confidence
    is weaker than the threshold.
    """
    stats = AnnotateStats()
    out: list[str] = []
    by_addr = kb.by_address
    by_name = kb.by_name
    emitted_headers: set[int] = set()
    sized = [e for e in kb.entries if e.end is not None]

    conf_rank = {c: i for i, c in enumerate(CONFIDENCE_ORDER)}
    # min_rank: emit headers for entries whose rank <= min_rank (0=confirmed only, 3=all)
    min_rank = conf_rank.get(min_confidence or "guess", len(CONFIDENCE_ORDER) - 1)

    current_region: tuple[int, str] | None = None

    for raw in source_lines:
        stats.lines_in += 1
        line = raw.rstrip("\n")

        addr = line_address(line, by_name)
        # Feature E: only fire region dividers from label lines, not from
        # addresses embedded in comments or inline operands (avoids false
        # triggers from file-header comment blocks).
        is_label = _LABEL_LINE_RE.match(line) is not None

        if addr is not None:
            if is_label:
                region = _region_for(addr)
                if region is not None and region != current_region:
                    current_region = region
                    out.extend(_region_divider(region[1]))

            # Header block for this address
            entry = by_addr.get(addr)
            if entry is not None and addr not in emitted_headers:
                emitted_headers.add(addr)
                rank = conf_rank.get(entry.confidence, len(CONFIDENCE_ORDER) - 1)
                if rank <= min_rank:
                    out.extend(_header_block(entry, kb))
                    stats.headers_emitted += 1

            # Inline region tag for interior addresses inside a sized entry
            # inside = next(
            #    (e for e in sized if e.address < addr and e.covers(addr)),
            #    None,
            # )
            # if inside is not None:
            #    line = (
            #        line.rstrip()
            #        + f"    ; ({inside.name} +{addr - inside.address:#x})"
            #    )
            #    stats.inline_annotations += 1

        # Feature A & B: resolve "; -> LABEL" comments
        line = _resolve_call_comments(line, kb)

        # Feature F: annotate CALL/JP/JR without an existing "; ->" comment
        line = _inline_annotation(line, kb)

        out.append(line.rstrip())

    stats.lines_out = len(out)
    return out, stats


# ---------------------------------------------------------------------------
# Source file analysis helpers (for coverage)
# ---------------------------------------------------------------------------


def _count_data_bytes(line: str) -> int:
    """Return byte count declared on a DB or DW line."""
    m = re.match(r"^\s+(DB|DEFB)\b(.+?)(?:\s*;.*)?$", line, re.IGNORECASE)
    if m:
        return len(m.group(2).split(","))
    m = re.match(r"^\s+(DW|DEFW)\b(.+?)(?:\s*;.*)?$", line, re.IGNORECASE)
    if m:
        return len(m.group(2).split(",")) * 2
    return 0


def _parse_source_segments(
    source_lines: list[str],
) -> list[tuple[int, str, int, int]]:
    """Parse source into segments between labels.

    Returns list of (addr, label, code_line_count, data_byte_count).
    Only labels with extractable hex addresses are included.
    """
    # Collect (addr, label, line_num) for labels with hex addresses
    label_positions: list[tuple[int, str, int]] = []
    for i, raw in enumerate(source_lines):
        m = _LABEL_LINE_RE.match(raw)
        if m:
            label = m.group(1)
            addr = _addr_from_label(label)
            if addr is not None:
                label_positions.append((addr, label, i))

    segments: list[tuple[int, str, int, int]] = []
    for idx, (addr, label, line_num) in enumerate(label_positions):
        end_line = (
            label_positions[idx + 1][2]
            if idx + 1 < len(label_positions)
            else len(source_lines)
        )
        code_lines = 0
        data_bytes = 0
        for raw in source_lines[line_num + 1 : end_line]:
            if _DATA_LINE_RE.match(raw):
                data_bytes += _count_data_bytes(raw)
            elif (
                _CODE_LINE_RE.match(raw)
                and raw.strip()
                and not raw.strip().startswith(";")
            ):
                code_lines += 1
        segments.append((addr, label, code_lines, data_bytes))
    return segments


# ---------------------------------------------------------------------------
# Coverage report
# ---------------------------------------------------------------------------


def coverage_report(
    kb: KB,
    source_lines: list[str] | None = None,
) -> str:
    from collections import Counter

    ROM_START, ROM_END = 0x4000, 0xBFFF
    ROM_SIZE = ROM_END - ROM_START + 1

    entries = kb.entries
    total = len(entries)

    # ── G: by kind ──────────────────────────────────────────────────────────
    by_kind: Counter[str] = Counter(e.kind for e in entries)

    # ── H: confidence per kind ──────────────────────────────────────────────
    # kind → confidence → count
    conf_by_kind: dict[str, Counter[str]] = {}
    for e in entries:
        conf_by_kind.setdefault(e.kind, Counter())[e.confidence] += 1

    # ── K: dark zones (gaps in KB coverage within the ROM range) ─────────────
    # Build sorted list of (start, end) from KB entries
    covered: list[tuple[int, int]] = []
    for e in entries:
        s = e.address
        if e.end is not None:
            end_b = e.end if e.end_exclusive else e.end + 1
        else:
            end_b = s + 1
        if s <= ROM_END and end_b > ROM_START:
            covered.append((max(s, ROM_START), min(end_b, ROM_END + 1)))
    covered.sort()

    # Merge overlapping intervals
    merged: list[tuple[int, int]] = []
    for s, e in covered:
        if merged and s <= merged[-1][1]:
            merged[-1] = (merged[-1][0], max(merged[-1][1], e))
        else:
            merged.append([s, e])
    merged = [tuple(x) for x in merged]

    # Find gaps
    dark_zones: list[tuple[int, int, int]] = []  # (start, end, size)
    cursor = ROM_START
    for s, e in merged:
        if s > cursor:
            dark_zones.append((cursor, s - 1, s - cursor))
        cursor = e
    if cursor <= ROM_END:
        dark_zones.append((cursor, ROM_END, ROM_END - cursor + 1))
    dark_zones.sort(key=lambda x: -x[2])

    bytes_covered = sum(e - s for s, e in merged)
    bytes_uncovered = ROM_SIZE - bytes_covered

    # ── M: orphans ───────────────────────────────────────────────────────────
    # Exclude BIOS / vector entries (0x0000-0x3FFF) which are external reference
    # points, not game code, and naturally have no intra-KB callers.
    orphans = [
        e
        for e in entries
        if not e.calls
        and not e.called_by
        and e.kind == "routine"
        and e.address >= 0x4000
    ]

    # ── N: sprint timeline ───────────────────────────────────────────────────
    by_sprint: Counter[str] = Counter(e.sprint for e in entries)

    # ── I & J: source analysis ───────────────────────────────────────────────
    source_stats: dict | None = None
    if source_lines is not None:
        segments = _parse_source_segments(source_lines)
        by_addr_map = kb.by_address
        # data entries with address ranges, for J coverage
        data_entries = [e for e in entries if e.kind == "data" and e.end is not None]
        total_code = sum(s[2] for s in segments)
        total_data_bytes = sum(s[3] for s in segments)
        unmapped_code = sum(s[2] for s in segments if by_addr_map.get(s[0]) is None)

        # J: compare KB-documented data byte ranges vs total raw DB bytes
        kb_data_bytes = sum(
            (e.end - e.address + (0 if e.end_exclusive else 1)) for e in data_entries
        )
        unmapped_data_bytes = max(0, total_data_bytes - kb_data_bytes)
        source_stats = {
            "total_code_lines": total_code,
            "total_data_bytes": total_data_bytes,
            "unmapped_code_lines": unmapped_code,
            "unmapped_data_bytes": unmapped_data_bytes,
            "pct_code_covered": 100 * (1 - unmapped_code / total_code)
            if total_code
            else 0,
            "pct_data_covered": 100 * (1 - unmapped_data_bytes / total_data_bytes)
            if total_data_bytes
            else 0,
        }

    # ── Render ───────────────────────────────────────────────────────────────
    lines: list[str] = []

    def _h(title: str) -> None:
        lines.append(f"\n## {title}\n")

    def _row(*cols: str) -> None:
        lines.append("| " + " | ".join(str(c) for c in cols) + " |")

    def _sep(*widths: int) -> None:
        lines.append("|" + "|".join("-" * (w + 2) for w in widths) + "|")

    lines.append("# Coverage Report\n")
    lines.append(
        f"**{total} KB entries** covering approximately "
        f"**{bytes_covered:,} / {ROM_SIZE:,} bytes** "
        f"({100 * bytes_covered / ROM_SIZE:.1f}%) of the {ROM_SIZE // 1024}KB ROM.\n"
    )

    # G: by kind with confidence breakdown
    _h("G — Entries by kind")
    _row("Kind", "Count", "% of entries", "confirmed", "likely", "hypothesis", "guess")
    _sep(12, 7, 13, 10, 7, 10, 6)
    for kind in sorted(by_kind, key=lambda k: -by_kind[k]):
        cnt = by_kind[kind]
        pct = f"{100 * cnt / total:.1f}%"
        cf = conf_by_kind.get(kind, Counter())
        _row(
            kind,
            cnt,
            pct,
            cf.get("confirmed", 0),
            cf.get("likely", 0),
            cf.get("hypothesis", 0),
            cf.get("guess", 0),
        )
    _row("**total**", f"**{total}**", "100%", "", "", "", "")
    lines.append("")

    # H: confidence pyramid
    _h("H — Confidence distribution")
    _row("Confidence", "Count", "% of entries")
    _sep(12, 7, 13)
    by_conf: Counter[str] = Counter(e.confidence for e in entries)
    for conf in CONFIDENCE_ORDER:
        cnt = by_conf.get(conf, 0)
        _row(conf, cnt, f"{100 * cnt / total:.1f}%")
    lines.append("")

    # I & J: source-level stats
    if source_stats is not None:
        _h("I — Unmapped code (instruction lines)")
        ss = source_stats
        mapped_code = ss["total_code_lines"] - ss["unmapped_code_lines"]
        _row("Category", "Lines", "% covered")
        _sep(20, 7, 10)
        _row(
            "Instruction lines (mapped)", mapped_code, f"{ss['pct_code_covered']:.1f}%"
        )
        _row("Instruction lines (unmapped)", ss["unmapped_code_lines"], "")
        _row("Total instruction lines", ss["total_code_lines"], "")
        lines.append("")

        _h("J — Unmapped data bytes")
        mapped_data = ss["total_data_bytes"] - ss["unmapped_data_bytes"]
        _row("Category", "Bytes", "% covered")
        _sep(20, 7, 10)
        _row("Data bytes (mapped)", mapped_data, f"{ss['pct_data_covered']:.1f}%")
        _row("Data bytes (unmapped)", ss["unmapped_data_bytes"], "")
        _row("Total data bytes", ss["total_data_bytes"], "")
        lines.append("")

    # K: dark zones
    _h("K — Dark zones (largest uncharted ROM ranges)")
    _row("Start", "End", "Bytes", "Notes")
    _sep(7, 7, 7, 30)
    for s, e, size in dark_zones[:20]:
        note = "—"
        for region_start, region_name in reversed(ROM_REGIONS):
            if s >= region_start:
                note = (
                    region_name.split("—")[-1].strip()
                    if "—" in region_name
                    else region_name
                )
                break
        _row(f"0x{s:04X}", f"0x{e:04X}", size, note)
    if len(dark_zones) > 20:
        lines.append(f"\n*(and {len(dark_zones) - 20} more smaller zones)*\n")
    lines.append("")

    # M: orphaned routines
    _h("M — Orphaned routines (no calls, no called_by)")
    if orphans:
        _row("Name", "Address", "Confidence")
        _sep(30, 9, 12)
        for o in sorted(orphans, key=lambda x: x.address):
            _row(o.name, o.addr_hex, o.confidence)
    else:
        lines.append("*(none)*\n")
    lines.append("")

    # N: sprint timeline
    _h("N — Entries per sprint (cumulative)")
    _row("Sprint", "New entries", "Cumulative")
    _sep(8, 12, 11)
    cumulative = 0
    for sprint in sorted(by_sprint):
        n = by_sprint[sprint]
        cumulative += n
        _row(sprint, n, cumulative)
    lines.append("")

    return "\n".join(lines) + "\n"
