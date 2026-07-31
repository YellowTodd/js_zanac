"""`zanackb` command-line interface."""

from __future__ import annotations

import sys
from pathlib import Path

import click

from . import __version__
from .annotate import annotate, coverage_report
from .emit_symbols import EMITTERS, emit
from .parser import load_kb
from .validate import validate


def _default_kb_root() -> Path:
    cur = Path.cwd().resolve()
    for d in [cur, *cur.parents]:
        if (d / "kb").is_dir():
            return d / "kb"
    return cur / "kb"


def _default_source() -> Path:
    cur = Path.cwd().resolve()
    for d in [cur, *cur.parents]:
        cand = d / "source" / "zanac.asm"
        if cand.exists():
            return cand
    return Path("source/zanac.asm")


KB_OPT = click.option(
    "--kb",
    "kb_root",
    type=click.Path(exists=True, file_okay=False, path_type=Path),
    default=None,
    help="Path to the kb/ directory (default: auto-detect).",
)


@click.group(context_settings={"help_option_names": ["-h", "--help"]})
@click.version_option(__version__)
def main() -> None:
    """Knowledge-base tools for the Zanac disassembly."""


@main.command("validate")
@KB_OPT
def validate_cmd(kb_root):
    """Validate the KB: schema, overlaps, broken references."""
    root = kb_root or _default_kb_root()
    try:
        kb = load_kb(root)
    except Exception as exc:
        click.echo(f"Load failed:\n{exc}", err=True)
        sys.exit(2)
    issues = validate(kb)
    errors = [i for i in issues if i.level == "error"]
    warnings = [i for i in issues if i.level == "warning"]
    for i in issues:
        click.echo(str(i))
    click.echo(
        f"\n{len(kb.entries)} entries, "
        f"{len(errors)} errors, {len(warnings)} warnings."
    )
    if errors:
        sys.exit(1)


@main.command("symbols")
@KB_OPT
@click.option(
    "--format",
    "fmt",
    type=click.Choice(sorted(EMITTERS)),
    default="openmsx",
    show_default=True,
)
@click.option(
    "-o",
    "--out",
    type=click.Path(dir_okay=False, path_type=Path),
    default=None,
    help="Output path (default: stdout).",
)
def symbols_cmd(kb_root, fmt, out):
    """Emit a symbol table for the openMSX debugger or an assembler."""
    kb = load_kb(kb_root or _default_kb_root())
    text = emit(kb, fmt)
    if out is None:
        click.echo(text, nl=False)
    else:
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(text, encoding="utf-8")
        click.echo(f"Wrote {len(kb.entries)} symbols to {out}", err=True)


@main.command("annotate")
@KB_OPT
@click.argument(
    "source",
    type=click.Path(dir_okay=False, path_type=Path),
    required=False,
)
@click.option(
    "-o",
    "--out",
    type=click.Path(dir_okay=False, path_type=Path),
    default=None,
    help="Output path (default: stdout).",
)
@click.option(
    "--min-confidence",
    type=click.Choice(["confirmed", "likely", "hypothesis", "guess"]),
    default=None,
    help="Suppress headers for entries below this confidence level.",
)
def annotate_cmd(kb_root, source, out, min_confidence):
    """Produce a fully commented copy of the disassembly."""
    kb = load_kb(kb_root or _default_kb_root())
    src = Path(source) if source else _default_source()
    if not src.exists():
        click.echo(f"Source not found: {src}", err=True)
        sys.exit(1)
    lines = src.read_text(encoding="utf-8").splitlines()
    annotated, stats = annotate(lines, kb, min_confidence=min_confidence)
    text = "\n".join(annotated) + "\n"
    if out is None:
        click.echo(text, nl=False)
    else:
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(text, encoding="utf-8")
    click.echo(
        f"Annotated {stats.lines_in} lines: "
        f"{stats.headers_emitted} headers, "
        f"{stats.inline_annotations} inline notes.",
        err=True,
    )


@main.command("coverage")
@KB_OPT
@click.argument(
    "source",
    type=click.Path(dir_okay=False, path_type=Path),
    required=False,
)
def coverage_cmd(kb_root, source):
    """Coverage report: confidence, kinds, dark zones, orphans, sprint timeline."""
    kb = load_kb(kb_root or _default_kb_root())
    src = Path(source) if source else _default_source()
    source_lines: list[str] | None = None
    if src.exists():
        source_lines = src.read_text(encoding="utf-8").splitlines()
    else:
        click.echo(f"Note: source not found ({src}), skipping I/J metrics.", err=True)
    click.echo(coverage_report(kb, source_lines), nl=False)


@main.command("refs")
@KB_OPT
@click.argument("address")
def refs_cmd(kb_root, address):
    """Show callers and callees for a given address."""
    addr = int(address, 16) if address.lower().startswith("0x") else int(address)
    kb = load_kb(kb_root or _default_kb_root())
    e = kb.find(addr)
    if e is None:
        click.echo(f"No entry at 0x{addr:04X}.", err=True)
        sys.exit(1)

    click.echo(f"{e.name} @ {e.addr_hex}  [{e.kind}, {e.confidence}]")
    if e.calls:
        click.echo("  calls:")
        for r in e.calls:
            tgt = kb.find(r) if isinstance(r, int) else None
            label = r if isinstance(r, str) else f"0x{r:04X}"
            click.echo(f"    - {label}" + (f"  ({tgt.name})" if tgt else ""))
    callers = [
        c for c in kb.entries
        if any(isinstance(r, int) and r == addr for r in c.calls)
    ]
    if callers:
        click.echo("  called by (inferred from KB):")
        for c in callers:
            click.echo(f"    - {c.addr_hex} ({c.name})")
    if e.called_by:
        click.echo("  called_by (declared):")
        for r in e.called_by:
            label = r if isinstance(r, str) else f"0x{r:04X}"
            click.echo(f"    - {label}")


if __name__ == "__main__":
    main()
