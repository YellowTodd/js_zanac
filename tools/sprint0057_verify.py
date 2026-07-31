#!/usr/bin/env python3
"""Sprint 0057 — live-confirm the sound-event catalogue.

Breakpoint on play_sound_event (0x5189); log the event number (reg A) and the
caller (return address on stack) during title screen and early gameplay.
"""
import sys, time
sys.path.insert(0, "tools")
from zanackb.zanac_game import ZanacGame

with ZanacGame.launch("source/zanac.rom") as game:
    msx = game.client
    msx.cmd("set ::evlog {}")
    bp = msx.cmd(
        "debug set_bp 0x5189 {} "
        "{lappend ::evlog [list [reg A] [format %04X [peek16 [reg SP]]]]}"
    )

    game.wait_for_title()
    time.sleep(1.5)                      # title music + any title SFX
    title_log = msx.cmd("set ::evlog")
    print("=== during title ===")
    print(title_log)

    msx.cmd("set ::evlog {}")
    game.start_game()                    # into gameplay
    time.sleep(2.0)
    game.shoot_shot()                    # fire → weapon SFX
    time.sleep(1.5)
    play_log = msx.cmd("set ::evlog")
    print("\n=== start + shooting ===")
    print(play_log)

    msx.cmd(f"debug remove_bp {bp}")
