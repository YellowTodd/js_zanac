"""Zanac-specific game controller built on top of OpenMsxClient.

## Screen-state detection (primary method)

Read the VRAM name table (0x3800–0x3AFF, 24×32 ASCII tile indices) and search
for game-specific text strings:

  "COMPILE"   → title screen (company logo shown, waiting for SPACE)
  "PAUSE"     → game paused (STOP key was pressed)
  "GAME OVER" → game-over screen
  "ZANAC"     → gameplay active (lives shown as ZANAC sprites)

These strings are unambiguous — only one appears at a time.

## Key addresses (confirmed from sprint analyses)

  0xE10A  lives remaining (0–3); 0 at title, 3 when game starts
  0xE10B  shot_level (0–5)
  0xE14B  fire_type  (0–7)
  0xE102  game state flags (mostly unused for detection; E102=0 in all states)
  0xE103  score_lo (BCD)
  0xE104  score_mid (BCD)
  0xE105  score_hi (BCD)
  0xE300  entity slot 0, byte 0: type (0x81 = player active, 0 = inactive)
  0xE304  entity slot 0, byte 4: color (0x81 = invincible, 0x8F = normal)

## Keyboard matrix (confirmed from source analysis, sprint 0017)

  Row 8 bit 0 (mask 0x01): SPACE — gameplay (both shot+fire; also title SPACE)
  Row 7 bit 2 (mask 0x04): ESC — title_screen_init secret: held while pressing SPACE → starts at round 0 (0xA65C)
  Row 8 bit 5 (mask 0x20): ↑ UP
  Row 8 bit 6 (mask 0x40): ↓ DOWN
  Row 8 bit 4 (mask 0x10): ← LEFT
  Row 8 bit 7 (mask 0x80): → RIGHT
  Row 6 bit 0 (mask 0x01): SHIFT — normal shot only
  Row 5 bit 7 (mask 0x80): Z — fire weapon only
  Row 7 bit 4 (mask 0x10): STOP — pauses the fire indicator
"""

from __future__ import annotations

import subprocess
import time
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator

from zanackb.openmsx import MSXKey, OpenMsxClient, OpenMsxError

# ── Zanac RAM addresses ───────────────────────────────────────────────────────

ADDR_LIVES = 0xE10A
ADDR_SHOT_LEVEL = 0xE10B
ADDR_FIRE_TYPE = 0xE14B
ADDR_SCORE_LO = 0xE103
ADDR_SCORE_MID = 0xE104
ADDR_SCORE_HI = 0xE105
ADDR_GAME_FLAGS = 0xE102
ADDR_PLAYER_TYPE = 0xE300
ADDR_PLAYER_COLOR = 0xE304

# VRAM name table (Screen 2, R2=0x0E → 0x0E×0x400 = 0x3800)
VRAM_NAME_TABLE = 0x3800
VRAM_NAME_SIZE = 0x300  # 24 rows × 32 cols

# Text strings that identify each screen state
TEXT_TITLE = "COMPILE"  # company logo on title screen
TEXT_PAUSED = "PAUSE"  # STOP key was pressed
TEXT_GAME_OVER = "GAME OVER"
TEXT_IN_GAME = "ZANAC"  # lives counter (ZANAC lettering)

COLOR_NORMAL = 0x8F
COLOR_INVINCIBLE = 0x81

ROM_DEFAULT = "source/zanac.rom"


# ── Screen state ─────────────────────────────────────────────────────────────


class ScreenState:
    TITLE = "title"
    IN_GAME = "in_game"
    PAUSED = "paused"
    GAME_OVER = "game_over"
    UNKNOWN = "unknown"


def detect_screen(name_table: str) -> str:
    """Classify the current screen from the VRAM name table text."""
    if TEXT_TITLE in name_table:
        return ScreenState.TITLE
    if TEXT_PAUSED in name_table:
        return ScreenState.PAUSED
    if TEXT_GAME_OVER in name_table:
        return ScreenState.GAME_OVER
    if TEXT_IN_GAME in name_table:
        return ScreenState.IN_GAME
    return ScreenState.UNKNOWN


# ── ZanacGame controller ──────────────────────────────────────────────────────


class ZanacGame:
    """High-level Zanac game controller.

    Typical usage::

        with ZanacGame.launch() as game:
            game.wait_for_title()
            game.start_game()
            game.steer(up=True)
            game.shoot_shot()
            if game.wait_for_collision(timeout=10):
                print("hit!")
            game.wait_for_game_over()
    """

    def __init__(self, client: OpenMsxClient, proc: subprocess.Popen | None = None):
        self.client = client
        self._proc = proc
        self._collision_wp: str | None = None
        self._kill_wp: str | None = None
        self._invincible_wp: str | None = None

    # ── factory / lifecycle ───────────────────────────────────────────────────

    @classmethod
    @contextmanager
    def launch(
        cls,
        rom: str | Path = ROM_DEFAULT,
        startup_timeout: float = 15.0,
    ) -> Iterator["ZanacGame"]:
        """Launch an openMSX instance, power on, yield a ZanacGame.

        Sets the BP at cold_start (0x4010) before powering on so we know
        when the BIOS has handed control to the cart. Terminates openMSX
        when the context exits.
        """
        client, proc = OpenMsxClient.connect_subprocess(
            rom=str(rom), timeout=startup_timeout
        )
        game = cls(client, proc)
        try:
            # Set cold_start BP before power-on to avoid a race
            client.cmd("set ::zanac_cold_start 0")
            bp = client.set_breakpoint(0x4010, "set ::zanac_cold_start 1")
            client.power_on()
            # Wait for BIOS to call cart INIT (~2s)
            client.poll_flag("zanac_cold_start", interval=0.3, timeout=10.0)
            client.remove_breakpoint(bp)
            yield game
        finally:
            game.cleanup()
            proc.terminate()
            proc.wait()

    @classmethod
    @contextmanager
    def attach(cls) -> Iterator["ZanacGame"]:
        """Attach to an already-running openMSX instance."""
        client = OpenMsxClient.autoconnect()
        game = cls(client)
        try:
            yield game
        finally:
            game.cleanup()
            client.close()

    def cleanup(self) -> None:
        """Remove watchpoints and release all keys."""
        for attr in ("_collision_wp", "_kill_wp", "_invincible_wp"):
            wp = getattr(self, attr)
            if wp:
                try:
                    self.client.remove_watchpoint(wp)
                except OpenMsxError:
                    pass
                setattr(self, attr, None)
        try:
            self.client.release_all_keys()
        except OpenMsxError:
            pass

    # ── screen detection ──────────────────────────────────────────────────────

    def screen_state(self) -> str:
        """Return the current ScreenState by reading the VRAM name table."""
        return detect_screen(self.client.read_name_table())

    def is_at_title(self) -> bool:
        return self.screen_state() == ScreenState.TITLE

    def is_in_game(self) -> bool:
        return self.screen_state() == ScreenState.IN_GAME

    def is_paused(self) -> bool:
        return self.screen_state() == ScreenState.PAUSED

    def is_game_over(self) -> bool:
        return self.screen_state() == ScreenState.GAME_OVER

    # ── game state reads ──────────────────────────────────────────────────────

    def lives(self) -> int:
        return self.client.read_byte(ADDR_LIVES)

    def score(self) -> int:
        lo = self.client.read_byte(ADDR_SCORE_LO)
        mid = self.client.read_byte(ADDR_SCORE_MID)
        hi = self.client.read_byte(ADDR_SCORE_HI)

        def bcd(b: int) -> int:
            return (b >> 4) * 10 + (b & 0x0F)

        return bcd(hi) * 10000 + bcd(mid) * 100 + bcd(lo)

    def shot_level(self) -> int:
        return self.client.read_byte(ADDR_SHOT_LEVEL)

    def fire_type(self) -> int:
        return self.client.read_byte(ADDR_FIRE_TYPE)

    def is_player_active(self) -> bool:
        return (self.client.read_byte(ADDR_PLAYER_TYPE) & 0x7F) == 1

    def is_invincible(self) -> bool:
        return self.client.read_byte(ADDR_PLAYER_COLOR) == COLOR_INVINCIBLE

    # ── phase waits ───────────────────────────────────────────────────────────

    def wait_for_title(self, timeout: float = 30.0) -> bool:
        """Wait until the title screen ('COMPILE') is visible."""
        deadline = time.time() + timeout
        while time.time() < deadline:
            if self.is_at_title():
                return True
            time.sleep(0.3)
        return False

    def start_game(self, timeout: float = 15.0) -> bool:
        """Hold SPACE until the title screen is gone and game is active.

        Injects SPACE on both keyboard rows the game checks:
          - row 7 bit 2 (snsmat row 7, Japanese layout SPACE / title check)
          - row 8 bit 0 (gameplay SPACE)
        Releases SPACE between presses to give the game a clean edge.
        """
        deadline = time.time() + timeout
        while time.time() < deadline:
            self.client.key_down(*MSXKey.ZANAC_SPACE)
            time.sleep(0.1)
            self.client.key_up(*MSXKey.ZANAC_SPACE)
            time.sleep(0.3)
            if self.is_in_game():
                return True
        return False

    def wait_for_game_start(self, timeout: float = 10.0) -> bool:
        deadline = time.time() + timeout
        while time.time() < deadline:
            if self.is_in_game():
                return True
            time.sleep(0.2)
        return False

    def wait_for_game_over(self, timeout: float = 120.0) -> bool:
        """Wait until 'GAME OVER' appears on screen."""
        deadline = time.time() + timeout
        while time.time() < deadline:
            if self.is_game_over():
                return True
            time.sleep(0.3)
        return False

    def skip_to_title(self, timeout: float = 20.0) -> bool:
        """From game-over screen, press SPACE to return to title."""
        deadline = time.time() + timeout
        while time.time() < deadline:
            self.client.key_press(*MSXKey.ZANAC_SPACE_TITLE, duration=0.1)
            time.sleep(0.4)
            if self.is_at_title():
                return True
        return False

    def wait_for_title_screen(self, timeout: float = 30.0) -> bool:
        """Wait until the title screen re-appears (e.g. after game over)."""
        return self.wait_for_title(timeout=timeout)

    # ── event detection ───────────────────────────────────────────────────────

    def arm_collision_detector(self) -> None:
        """Watch lives (0xE10A) for a decrease — signals ship hit."""
        if self._collision_wp:
            return
        self.client.cmd("set ::zanac_collision 0")
        self.client.cmd(f"set ::zanac_prev_lives {self.lives()}")
        self._collision_wp = self.client.set_watchpoint(
            "write_mem",
            ADDR_LIVES,
            condition=f"[debug read memory {ADDR_LIVES}] < $::zanac_prev_lives",
            tcl_action=(
                f"set ::zanac_prev_lives [debug read memory {ADDR_LIVES}]; "
                "set ::zanac_collision 1"
            ),
        )

    def check_collision(self) -> bool:
        if self.client.cmd("set ::zanac_collision") == "1":
            self.client.cmd("set ::zanac_collision 0")
            return True
        return False

    def wait_for_collision(self, timeout: float = 30.0) -> bool:
        self.arm_collision_detector()
        return self.client.poll_flag("zanac_collision", interval=0.1, timeout=timeout)

    def arm_kill_detector(self) -> None:
        """Watch score_lo (0xE103) writes — proxy for scoring an enemy kill."""
        if self._kill_wp:
            return
        self.client.cmd("set ::zanac_kill_count 0")
        self._kill_wp = self.client.set_watchpoint(
            "write_mem",
            ADDR_SCORE_LO,
            tcl_action="incr ::zanac_kill_count",
        )

    def kill_count(self) -> int:
        n = int(self.client.cmd("set ::zanac_kill_count"))
        self.client.cmd("set ::zanac_kill_count 0")
        return n

    def wait_for_enemy_kill(self, timeout: float = 30.0) -> bool:
        self.arm_kill_detector()
        return self.client.poll_flag("zanac_kill_count", interval=0.1, timeout=timeout)

    # ── ship control ──────────────────────────────────────────────────────────

    def steer(
        self,
        up: bool = False,
        down: bool = False,
        left: bool = False,
        right: bool = False,
    ) -> None:
        """Set directional keys. Call with no args to stop."""
        self.client.key_up(8, 0x80 | 0x40 | 0x20 | 0x10)
        mask = 0
        if up:
            mask |= 0x20
        if down:
            mask |= 0x40
        if left:
            mask |= 0x10
        if right:
            mask |= 0x80
        if mask:
            self.client.key_down(8, mask)

    def shoot_shot(self) -> None:
        """Hold SHIFT (normal shot)."""
        self.client.key_down(*MSXKey.ZANAC_SHOT)

    def release_shot(self) -> None:
        self.client.key_up(*MSXKey.ZANAC_SHOT)

    def fire_shot(self, duration: float = 0.08) -> None:
        """Tap SHIFT for one shot."""
        self.client.key_press(*MSXKey.ZANAC_SHOT, duration=duration)

    def shoot_fire(self) -> None:
        """Hold Z (fire weapon)."""
        self.client.key_down(*MSXKey.ZANAC_FIRE)

    def release_fire(self) -> None:
        self.client.key_up(*MSXKey.ZANAC_FIRE)

    def fire_weapon(self, duration: float = 0.08) -> None:
        """Tap Z for one fire weapon burst."""
        self.client.key_press(*MSXKey.ZANAC_FIRE, duration=duration)

    def shoot_both(self) -> None:
        """Hold SPACE (fires both shot and fire weapon)."""
        self.client.key_down(*MSXKey.ZANAC_SPACE_PLAY)

    def release_both(self) -> None:
        self.client.key_up(*MSXKey.ZANAC_SPACE_PLAY)

    def release_weapons(self) -> None:
        self.client.key_up(*MSXKey.ZANAC_SHOT)
        self.client.key_up(*MSXKey.ZANAC_FIRE)
        self.client.key_up(*MSXKey.ZANAC_SPACE_PLAY)

    def press_stop(self, duration: float = 0.08) -> None:
        """Tap STOP (pauses the fire indicator display)."""
        self.client.key_press(*MSXKey.ZANAC_STOP, duration=duration)

    # ── game manipulation ─────────────────────────────────────────────────────

    def arm_warp(self, round: int) -> None:
        """Arm a one-shot warp to round 0–8. Call before start_game().

        Sets a breakpoint at 0x425A (inside title_screen_init) that fires when
        the player presses SPACE on the title screen, patching 0xE701 to select
        the desired round's level-start address. The breakpoint removes itself
        after firing.

        Round map: 0 = secret, 1 = normal start, 2–8 = later areas.
        """
        if not 0 <= round <= 8:
            raise ValueError(f"round must be 0–8, got {round}")
        msx = self.client
        msx.cmd(f"set ::_warp_round {round}")
        msx.cmd(
            "set ::_warp_bp [debug set_bp 0x425A {} {"
            "debug write memory 0xE701 $::_warp_round; "
            "debug remove_bp $::_warp_bp; "
            "unset -nocomplain ::_warp_round ::_warp_bp}]"
        )

    def make_invincible(self) -> None:
        """Make the player permanently invincible for the current session.

        Sets the invincibility flag (0xE305 bit 7) and arms a watchpoint that
        reloads the invincibility timer (0xE31B) to 255 whenever the game writes
        to it, preventing the timer from ever expiring. Safe to call multiple
        times; the watchpoint is replaced if already armed.
        """
        msx = self.client
        if self._invincible_wp:
            try:
                msx.remove_watchpoint(self._invincible_wp)
            except OpenMsxError:
                pass
        msx.write_byte(0xE305, msx.read_byte(0xE305) | 0x80)
        msx.write_byte(0xE31B, 0xFF)
        self._invincible_wp = msx.set_watchpoint(
            "write_mem",
            0xE31B,
            tcl_action="debug write memory 0xE31B 255",
        )

    def spawn_type(self, type_id: int, y: int = 100, x: int = 120) -> int:
        """Inject entity type_id into the first free enemy slot (indices 5–24).

        Matches spawn_type.tcl behaviour: briefly refreshes the invincibility
        timer so the game keeps running during injection. The entity type is
        written without the active flag (bit 7), so entity_dispatch runs the
        handler's init path on the very next cycle.

        Returns the slot index (5–24), or -1 if all slots are occupied.
        """
        msx = self.client
        # Brief invincibility window (one-shot, no persistent watchpoint)
        msx.write_byte(0xE305, msx.read_byte(0xE305) | 0x80)
        msx.write_byte(0xE31B, 0xFF)
        for i in range(5, 25):
            addr = 0xE300 + i * 32
            if msx.read_byte(addr) == 0:
                msx.write_memory(addr, bytes(32))  # zero-init the slot
                msx.write_byte(addr + 1, y)
                msx.write_byte(addr + 2, x)
                msx.write_byte(addr, type_id)  # bit7 clear → init on first dispatch
                return i
        return -1
