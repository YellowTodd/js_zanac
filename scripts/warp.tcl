# scripts/warp.tcl — Warp to any round at the Zanac title screen
#
# Usage (in the openMSX TCL console):
#   source scripts/warp.tcl
#   warp 3        ;# arm warp to round 3, then press SPACE on title screen
#
# Rounds 1–8 are the normal in-game areas (1 = normal start, 8 = final area).
# Round 0 is the secret bonus round, normally reached via warp orbs in-game.
#
# Implementation:
#   Breaks at 0x425A (LAB_425a inside title_screen_init), which is the point
#   where E701 (stage index) is read to index into the 8-entry level-start
#   table at 0x945C.  Writing E701 here selects any of the 9 valid start
#   addresses before the level-streaming engine is initialised.

proc warp {round} {
    if {![string is integer -strict $round] || $round < 0 || $round > 8} {
        puts "Usage: warp <round>  (0 = secret, 1 = normal start, 2..8 = later areas)"
        return
    }

    # One-shot breakpoint at LAB_425a (0x425A).
    # When fired: overwrite E701, then remove itself.
    set ::_warp_round $round
    set ::_warp_bp [debug set_bp 0x425A {} {
        debug write "memory" 0xE701 $::_warp_round
        debug remove_bp $::_warp_bp
        puts "Warped to round $::_warp_round."
        unset -nocomplain ::_warp_round ::_warp_bp
    }]

    puts "Warp to round $round armed — press SPACE (or SHIFT / Z) on the title screen."
}
