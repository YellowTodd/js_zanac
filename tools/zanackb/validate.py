"""Cross-entry validation: overlaps, broken cross-references, dangling names."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

from .parser import KB, SymbolEntry


@dataclass
class ValidationIssue:
    level: str  # "error" or "warning"
    where: str
    message: str

    def __str__(self) -> str:
        return f"[{self.level.upper()}] {self.where}: {self.message}"


def _intervals(e: SymbolEntry) -> tuple[int, int]:
    if e.end is None:
        return (e.address, e.address)
    end = e.end - 1 if e.end_exclusive else e.end
    return (e.address, end)


def check_overlaps(kb: KB) -> Iterable[ValidationIssue]:
    by_addr = sorted(kb.entries, key=lambda e: e.address)
    for i, a in enumerate(by_addr):
        a_lo, a_hi = _intervals(a)
        for b in by_addr[i + 1 :]:
            b_lo, b_hi = _intervals(b)
            if b_lo > a_hi:
                break  # sorted, no further overlap possible
            yield ValidationIssue(
                "error",
                f"{a.source_path} <-> {b.source_path}",
                f"address ranges overlap: "
                f"{a.name}@{a.addr_hex}-{a_hi:#06X} vs "
                f"{b.name}@{b.addr_hex}-{b_hi:#06X}",
            )


def check_refs(kb: KB) -> Iterable[ValidationIssue]:
    addrs = set(kb.by_address)
    for e in kb.entries:
        for ref in e.calls:
            if isinstance(ref, int) and ref not in addrs:
                yield ValidationIssue(
                    "warning",
                    str(e.source_path),
                    f"{e.name} calls 0x{ref:04X} which has no KB entry",
                )


def check_unique_names(kb: KB) -> Iterable[ValidationIssue]:
    seen: dict[str, SymbolEntry] = {}
    for e in kb.entries:
        if e.name in seen:
            other = seen[e.name]
            yield ValidationIssue(
                "error",
                f"{e.source_path} <-> {other.source_path}",
                f"duplicate name {e.name!r} at "
                f"{e.addr_hex} and {other.addr_hex}",
            )
        else:
            seen[e.name] = e


def check_sprint_ids(kb: KB) -> Iterable[ValidationIssue]:
    for e in kb.entries:
        s = str(e.sprint)
        if not (s.isdigit() and len(s) == 4):
            yield ValidationIssue(
                "warning",
                str(e.source_path),
                f"sprint id {s!r} should be a 4-digit string like '0001'",
            )


CHECKS = [check_overlaps, check_refs, check_unique_names, check_sprint_ids]


def validate(kb: KB) -> list[ValidationIssue]:
    issues: list[ValidationIssue] = []
    for check in CHECKS:
        issues.extend(check(kb))
    return issues
