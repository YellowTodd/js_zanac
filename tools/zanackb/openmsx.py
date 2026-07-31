"""Minimal openMSX control-protocol client.

openMSX exposes a TCL interpreter via a unix-domain socket created when it
is launched with `-control stdio`.  The socket appears at:

    $TMPDIR/openmsx-<username>/socket.<pid>

Wire format: plain UTF-8 XML, no length prefix.

Handshake (connection startup):
    client → <openmsx-control>\\n   (send immediately, before reading)
    server → <openmsx-output>…      (async preamble, discarded)

Command / reply cycle:
    client → <command>TCL</command>
    server → <reply result="ok">RESULT</reply>   (or result="nok")
"""

from __future__ import annotations

import os
import socket
import subprocess
import time
import xml.etree.ElementTree as ET
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator


class OpenMsxError(RuntimeError):
    """Raised when openMSX returns result="nok" or the channel is closed."""


# ── MSX keyboard matrix constants ─────────────────────────────────────────────
#
# Source: MSX Technical Handbook, International layout.
# SNSMAT(row) returns a byte where bit=0 means the key IS pressed,
# bit=1 means it is NOT pressed.
#
# keymatrixdown row mask  → force the bits in mask to 0 (pressed)
# keymatrixup   row mask  → restore those bits to 1 (released)


class MSXKey:
    """(row, bitmask) pairs for commonly needed keys."""

    # Row 8 — cursor and SPACE
    SPACE = (8, 0x01)  # bit 0
    HOME = (8, 0x02)  # bit 1
    INS = (8, 0x04)  # bit 2
    DEL = (8, 0x08)  # bit 3
    LEFT = (8, 0x10)  # bit 4  ←
    UP = (8, 0x20)  # bit 5  ↑
    DOWN = (8, 0x40)  # bit 6  ↓
    RIGHT = (8, 0x80)  # bit 7  →

    # Row 7 — function/control row
    F4 = (7, 0x01)
    F5 = (7, 0x02)
    ESC = (7, 0x04)  # also the Japanese SPACE on row 7 bit 2
    TAB = (7, 0x08)
    STOP = (7, 0x10)  # bit 4 — pauses the Zanac game display
    BS = (7, 0x20)
    SEL = (7, 0x40)
    RET = (7, 0x80)

    # Row 6 — modifier keys
    SHIFT = (6, 0x01)  # bit 0
    CTRL = (6, 0x02)
    GRAPH = (6, 0x04)
    CAPS = (6, 0x08)
    CODE = (6, 0x10)
    F1 = (6, 0x20)
    F2 = (6, 0x40)
    F3 = (6, 0x80)

    # Row 5 — S…Z
    S = (5, 0x01)
    T = (5, 0x02)
    U = (5, 0x04)
    V = (5, 0x08)
    W = (5, 0x10)
    X = (5, 0x20)
    Y = (5, 0x40)
    Z = (5, 0x80)

    # Row 4 — K…R
    K = (4, 0x01)
    L = (4, 0x02)
    M = (4, 0x04)
    N = (4, 0x08)
    O = (4, 0x10)
    P = (4, 0x20)
    Q = (4, 0x40)
    R = (4, 0x80)

    # Row 3 — C…J
    C = (3, 0x01)
    D = (3, 0x02)
    E = (3, 0x04)
    F = (3, 0x08)
    G = (3, 0x10)
    H = (3, 0x20)
    I = (3, 0x40)
    J = (3, 0x80)

    # Row 2 — A, B
    A = (2, 0x40)
    B = (2, 0x80)

    # Row 0 — digit keys
    DIGIT = {str(i): (0, 1 << i) for i in range(8)}  # '0'–'7'

    # Zanac-specific aliases (confirmed from source analysis, sprint 0017)
    ZANAC_ESC = (7, 0x04)  # row 7 bit 2: ESC
    ZANAC_SPACE = (8, 0x01)  # row 8 bit 0: SPACE (both shot+fire during gameplay)
    ZANAC_SHOT = (6, 0x01)  # SHIFT — normal shot only
    ZANAC_FIRE = (5, 0x80)  # Z — secondary fire weapon only
    ZANAC_UP = (8, 0x20)  # ↑
    ZANAC_DOWN = (8, 0x40)  # ↓
    ZANAC_LEFT = (8, 0x10)  # ←
    ZANAC_RIGHT = (8, 0x80)  # →
    ZANAC_STOP = (7, 0x10)  # STOP — pauses the weapon indicator display


class OpenMsxClient:
    """Thin wrapper around the openMSX TCL command socket."""

    def __init__(self, sock: socket.socket):
        self._sock = sock
        self._buf = b""
        # Send control header immediately — before reading anything.
        self._sock.sendall(b"<openmsx-control>\n")
        # Discard the <openmsx-output …> opening tag.
        self._read_until(b">")

    # ── factory helpers ────────────────────────────────────────────────────────

    @classmethod
    def connect_unix(cls, path: str | os.PathLike[str]) -> "OpenMsxClient":
        s = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        s.connect(str(path))
        return cls(s)

    @classmethod
    def _socket_dirs(cls) -> list[Path]:
        """Candidate directories where openMSX places its socket."""
        user = os.environ.get("USER", os.environ.get("LOGNAME", "user"))
        return [
            Path(os.environ.get("TMPDIR", "/tmp")) / f"openmsx-{user}",
            Path.home() / ".openMSX" / "sockets",
            Path("/tmp") / f"openmsx-{user}",
        ]

    @classmethod
    def _wait_for_socket(cls, pid: int, timeout: float = 15.0) -> Path | None:
        """Poll for `socket.<pid>` under candidate dirs; return path or None."""
        deadline = time.time() + timeout
        while time.time() < deadline:
            for d in cls._socket_dirs():
                if d.is_dir():
                    p = d / f"socket.{pid}"
                    if p.exists():
                        return p
            time.sleep(0.2)
        return None

    @classmethod
    def connect_subprocess(
        cls,
        rom: str | os.PathLike[str] | None = None,
        extra_args: tuple[str, ...] = (),
        timeout: float = 15.0,
    ) -> tuple["OpenMsxClient", subprocess.Popen[bytes]]:
        """Launch openMSX with `-control stdio`, wait for socket, connect.

        Returns ``(client, proc)``.  Caller must call ``proc.terminate()`` when done.
        ``-control stdio`` also forces headless (renderer=none) mode, which is
        intentional for automated scripts.
        """
        cmd: list[str] = ["openmsx", "-control", "stdio"]
        if rom is not None:
            cmd += ["-cart", str(rom)]
        cmd += list(extra_args)

        proc = subprocess.Popen(
            cmd,
            stdin=subprocess.PIPE,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )

        sock_path = cls._wait_for_socket(proc.pid, timeout=timeout)
        if sock_path is None:
            proc.terminate()
            proc.wait()
            dirs = ", ".join(str(d) for d in cls._socket_dirs())
            raise OpenMsxError(
                f"openMSX (pid {proc.pid}) did not create a socket within "
                f"{timeout:.0f}s (checked: {dirs})"
            )

        return cls.connect_unix(sock_path), proc

    @classmethod
    def autoconnect(cls) -> "OpenMsxClient":
        """Connect to the most-recently modified socket under candidate dirs."""
        candidates: list[Path] = []
        for d in cls._socket_dirs():
            if d.is_dir():
                candidates.extend(d.glob("socket.*"))
        if not candidates:
            dirs = ", ".join(str(d) for d in cls._socket_dirs())
            raise OpenMsxError(f"no openMSX socket found under: {dirs}")
        return cls.connect_unix(max(candidates, key=lambda p: p.stat().st_mtime))

    # ── raw protocol ──────────────────────────────────────────────────────────

    def _read_until(self, marker: bytes) -> bytes:
        while marker not in self._buf:
            chunk = self._sock.recv(4096)
            if not chunk:
                raise OpenMsxError("openMSX closed the connection")
            self._buf += chunk
        idx = self._buf.index(marker) + len(marker)
        head, self._buf = self._buf[:idx], self._buf[idx:]
        return head

    def _send(self, payload: str) -> None:
        msg = f"<command>{_xml_escape(payload)}</command>"
        self._sock.sendall(msg.encode("utf-8"))

    def _recv_reply(self) -> str:
        data = self._read_until(b"</reply>")
        text = data.decode("utf-8", errors="replace")
        # Pick the last <reply …>…</reply> block (skips interleaved <log>/<update>).
        start = text.rfind("<reply")
        end = text.rfind("</reply>") + len("</reply>")
        root = ET.fromstring(text[start:end])
        result = root.attrib.get("result", "nok")
        body = (root.text or "").strip()
        if result != "ok":
            raise OpenMsxError(body or "openMSX returned nok")
        return body

    def cmd(self, tcl: str) -> str:
        """Run a TCL command and return its result string."""
        self._send(tcl)
        return self._recv_reply()

    # ── memory ────────────────────────────────────────────────────────────────

    def power_on(self) -> None:
        """Power the MSX on. Required before the CPU will execute instructions."""
        self.cmd("set power on")

    def read_memory(self, addr: int, n: int) -> bytes:
        """Read *n* bytes from CPU address space starting at *addr*.

        Uses ``binary scan`` so that the result is hex-encoded and XML-safe.
        """
        hex_str = self.cmd(
            f"binary scan [debug read_block memory {addr} {n}] H* h; set h"
        )
        return bytes.fromhex(hex_str)

    def read_byte(self, addr: int) -> int:
        """Read a single byte from CPU address space (0–255)."""
        return int(self.cmd(f"debug read memory {addr}"))

    def read_vram(self, offset: int, n: int) -> bytes:
        """Read *n* bytes from VRAM starting at *offset*."""
        return self.read_debuggable("VRAM", offset, n)

    def read_name_table(self) -> str:
        """Read the 768-byte Screen-2 name table (VRAM 0x3800–0x3AFF) as a string.

        Non-ASCII bytes are replaced with spaces so standard ``in`` checks work.
        The name table maps 24 rows × 32 columns of tile indices; for Zanac these
        tile codes match ASCII for all on-screen text characters.
        """
        raw = self.read_vram(0x3800, 0x300)
        return "".join(chr(b) if 0x20 <= b < 0x7F else " " for b in raw)

    def read_debuggable(self, name: str, offset: int, n: int) -> bytes:
        """Read *n* bytes from a named openMSX debuggable."""
        hex_str = self.cmd(
            f"binary scan [debug read_block {{{name}}} {offset} {n}] H* h; set h"
        )
        return bytes.fromhex(hex_str)

    def write_memory(self, addr: int, data: bytes) -> None:
        for i, b in enumerate(data):
            self.cmd(f"debug write memory {addr + i} {b}")

    def write_byte(self, addr: int, value: int) -> None:
        """Write a single byte to CPU address space."""
        self.cmd(f"debug write memory {addr} {value}")

    # ── execution control ─────────────────────────────────────────────────────

    def step(self) -> None:
        self.cmd("debug step")

    def cont(self) -> None:
        self.cmd("debug cont")

    def reset(self) -> None:
        self.cmd("reset")

    def is_running(self) -> bool:
        """Return True if the CPU is currently running (not paused).

        Uses ``debug breaked`` which returns 1 when paused, 0 when running.
        """
        return self.cmd("debug breaked") == "0"

    # ── breakpoints & watchpoints ─────────────────────────────────────────────

    def set_breakpoint(self, addr: int, tcl_action: str = "") -> str:
        """Register a breakpoint; return the ``bp#N`` id assigned by openMSX."""
        action = "{" + tcl_action + "}" if tcl_action else "{}"
        return self.cmd(f"debug set_bp {addr} true {action}")

    def remove_breakpoint(self, bp_id: str) -> None:
        self.cmd(f"debug remove_bp {bp_id}")

    def set_watchpoint(
        self,
        wp_type: str,
        addr: int,
        condition: str = "",
        tcl_action: str = "",
    ) -> str:
        """Set a watchpoint; return its ``wp#N`` id.

        wp_type: "read_mem", "write_mem", "read_io", "write_io"
        condition: TCL expression, e.g. "[debug read memory 0xe10a] < 3"
        tcl_action: TCL to execute when fired, e.g. "set ::flag 1; debug break"
        """
        cond = "{" + condition + "}" if condition else "{}"
        action = "{" + tcl_action + "}" if tcl_action else "{}"
        return self.cmd(f"debug set_watchpoint {wp_type} {addr} {cond} {action}")

    def remove_watchpoint(self, wp_id: str) -> None:
        self.cmd(f"debug remove_watchpoint {wp_id}")

    def poll_flag(
        self, flag: str, interval: float = 0.2, timeout: float = 30.0
    ) -> bool:
        """Poll a TCL global variable until it becomes "1" (or timeout)."""
        deadline = time.time() + timeout
        while time.time() < deadline:
            time.sleep(interval)
            if self.cmd(f"set ::{flag}") == "1":
                return True
        return False

    # ── keyboard matrix ───────────────────────────────────────────────────────
    #
    # SNSMAT returns bit=0 for pressed, bit=1 for not-pressed.
    # keymatrixdown forces bits to 0; keymatrixup restores them to 1.

    def key_down(self, row: int, mask: int) -> None:
        """Press key(s): set the given row bits to 0 (pressed state)."""
        self.cmd(f"keymatrixdown {row} {mask}")

    def key_up(self, row: int, mask: int) -> None:
        """Release key(s): restore the given row bits to 1 (released state)."""
        self.cmd(f"keymatrixup {row} {mask}")

    def key_press(
        self,
        row: int,
        mask: int,
        duration: float = 0.08,
    ) -> None:
        """Press and release a key after *duration* seconds."""
        self.key_down(row, mask)
        time.sleep(duration)
        self.key_up(row, mask)

    def key_press_named(self, key: tuple[int, int], duration: float = 0.08) -> None:
        """Press and release an ``MSXKey`` constant (row, mask) tuple."""
        self.key_press(key[0], key[1], duration)

    def keys_down(self, *keys: tuple[int, int]) -> None:
        """Hold multiple MSXKey constants simultaneously."""
        for row, mask in keys:
            self.key_down(row, mask)

    def keys_up(self, *keys: tuple[int, int]) -> None:
        """Release multiple MSXKey constants simultaneously."""
        for row, mask in keys:
            self.key_up(row, mask)

    def release_all_keys(self) -> None:
        """Release all keyboard rows (safety reset after key injection)."""
        for row in range(11):
            self.cmd(f"keymatrixup {row} 0xff")

    def close(self) -> None:
        try:
            self._sock.close()
        except OSError:
            pass


def _xml_escape(s: str) -> str:
    return (
        s.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )


@contextmanager
def openmsx_session(
    rom: str | os.PathLike[str] | None = None,
) -> Iterator[OpenMsxClient]:
    """Context manager that provides a connected ``OpenMsxClient``.

    If *rom* is given, launches a fresh openMSX subprocess and terminates it
    on exit.  Otherwise, attaches to the most-recently started running instance.
    """
    if rom is not None:
        client, proc = OpenMsxClient.connect_subprocess(rom=rom)
        try:
            yield client
        finally:
            client.close()
            proc.terminate()
            proc.wait()
    else:
        client = OpenMsxClient.autoconnect()
        try:
            yield client
        finally:
            client.close()
