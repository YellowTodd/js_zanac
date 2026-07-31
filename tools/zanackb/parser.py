"""KB parsing: pydantic schema + Markdown-with-frontmatter loader.

Every file under `kb/symbols/` and `kb/data/` is loaded into a `SymbolEntry`.
The body of the Markdown file is preserved as `body` for later annotation.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable, Literal, Union

import frontmatter
from pydantic import BaseModel, BeforeValidator, ConfigDict, Field, field_validator
from typing_extensions import Annotated

# --- address parsing --------------------------------------------------------

HEX_RE = re.compile(r"^0x[0-9A-Fa-f]+$")
NAME_ROUTINE_RE = re.compile(r"^[a-z][a-z0-9_]*$")
NAME_CONSTANT_RE = re.compile(r"^[A-Z][A-Z0-9_]*$")
BIOS_REF_RE = re.compile(r"^BIOS:[A-Z][A-Z0-9_]*$")


def _coerce_address(v: Any) -> int:
    """Accept either an int (already parsed by YAML's 0xNNNN literal) or a
    string like '0x4123'."""
    if isinstance(v, int):
        return v
    if isinstance(v, str):
        s = v.strip()
        if HEX_RE.match(s):
            return int(s, 16)
        # also accept plain decimal so humans can grep
        if s.isdigit():
            return int(s, 10)
        raise ValueError(f"address must be 0xNNNN or decimal, got {v!r}")
    raise TypeError(f"address must be int or string, got {type(v).__name__}")


def _coerce_ref(v: Any) -> Union[int, str]:
    """A cross-reference is either an address (int) or a BIOS:NAME string."""
    if isinstance(v, int):
        return v
    if isinstance(v, str):
        s = v.strip()
        if HEX_RE.match(s):
            return int(s, 16)
        if BIOS_REF_RE.match(s):
            return s
        raise ValueError(f"reference must be 0xNNNN or BIOS:NAME, got {v!r}")
    raise TypeError(f"reference must be int or string, got {type(v).__name__}")


Address = Annotated[int, BeforeValidator(_coerce_address)]
Ref = Annotated[Union[int, str], BeforeValidator(_coerce_ref)]

Kind = Literal["routine", "data", "constant", "struct", "port"]
Confidence = Literal["confirmed", "likely", "hypothesis", "guess"]


# --- schema ----------------------------------------------------------------


class SymbolEntry(BaseModel):
    """One KB entry. Mirrors the frontmatter of a `kb/{symbols,data}/*.md`."""

    model_config = ConfigDict(extra="forbid")  # reject typos in field names

    address: Address
    end: Address | None = None
    end_exclusive: bool = False
    kind: Kind
    name: str
    confidence: Confidence
    sprint: str | int

    # routine-specific (optional)
    inputs: dict[str, str] = Field(default_factory=dict)
    outputs: dict[str, str] = Field(default_factory=dict)
    clobbers: list[str] = Field(default_factory=list)
    calls: list[Ref] = Field(default_factory=list)
    called_by: list[Ref] = Field(default_factory=list)

    # data-specific (optional)
    format: str | None = None  # e.g. "psg_track", "sprite_pattern_8x16"
    length: int | None = None

    # generic
    tags: list[str] = Field(default_factory=list)

    # populated by the loader, not present in frontmatter:
    source_path: Path | None = None
    body: str = ""

    @field_validator("sprint", mode="before")
    @classmethod
    def _sprint_to_str(cls, v: Any) -> str:
        # accept `0002` or `2` from YAML and store as a zero-padded string
        if isinstance(v, int):
            return f"{v:04d}"
        if isinstance(v, str):
            return v.strip()
        raise ValueError(f"sprint must be int or string, got {v!r}")

    @field_validator("name")
    @classmethod
    def _check_name(cls, v: str, info) -> str:
        kind = info.data.get("kind")
        if kind == "constant":
            if not NAME_CONSTANT_RE.match(v):
                raise ValueError(
                    f"constants must be SCREAMING_SNAKE_CASE, got {v!r}"
                )
        else:
            if not NAME_ROUTINE_RE.match(v):
                raise ValueError(
                    f"{kind} names must be snake_case, got {v!r}"
                )
        return v

    @field_validator("tags", mode="after")
    @classmethod
    def _check_tags(cls, v: list[str]) -> list[str]:
        for t in v:
            if not re.match(r"^[a-z][a-z0-9-]*$", t):
                raise ValueError(
                    f"tags must be lowercase, hyphenated; got {t!r}"
                )
        return v

    # convenience
    @property
    def addr_hex(self) -> str:
        return f"0x{self.address:04X}"

    @property
    def end_hex(self) -> str | None:
        return None if self.end is None else f"0x{self.end:04X}"

    def covers(self, addr: int) -> bool:
        if self.end is None:
            return addr == self.address
        if self.end_exclusive:
            return self.address <= addr < self.end
        return self.address <= addr <= self.end


# --- KB loader -------------------------------------------------------------


@dataclass
class KB:
    """In-memory index of all KB entries."""

    entries: list[SymbolEntry]

    @property
    def by_address(self) -> dict[int, SymbolEntry]:
        return {e.address: e for e in self.entries}

    @property
    def by_name(self) -> dict[str, SymbolEntry]:
        return {e.name: e for e in self.entries}

    def find(self, addr: int) -> SymbolEntry | None:
        return self.by_address.get(addr)

    def covering(self, addr: int) -> SymbolEntry | None:
        for e in self.entries:
            if e.covers(addr):
                return e
        return None


def load_entry(path: Path) -> SymbolEntry:
    """Load one Markdown-with-frontmatter file into a `SymbolEntry`."""
    post = frontmatter.load(path)
    data = dict(post.metadata)
    entry = SymbolEntry.model_validate(data)
    # mutate post-construction (these aren't in frontmatter)
    object.__setattr__(entry, "source_path", path)
    object.__setattr__(entry, "body", post.content)
    return entry


def load_kb(kb_root: Path) -> KB:
    """Walk `kb/symbols/` and `kb/data/` and load every `.md` file."""
    entries: list[SymbolEntry] = []
    errors: list[str] = []
    for sub in ("symbols", "data"):
        root = kb_root / sub
        if not root.exists():
            continue
        for path in sorted(root.rglob("*.md")):
            try:
                entries.append(load_entry(path))
            except Exception as exc:  # noqa: BLE001 — we want all errors
                errors.append(f"{path}: {exc}")
    if errors:
        raise ValueError(
            "Failed to load KB:\n  " + "\n  ".join(errors)
        )
    return KB(entries=entries)


def iter_sprint_files(kb_root: Path) -> Iterable[Path]:
    sprint_dir = kb_root / "sprints"
    if not sprint_dir.exists():
        return []
    return sorted(sprint_dir.glob("[0-9]*.md"))
