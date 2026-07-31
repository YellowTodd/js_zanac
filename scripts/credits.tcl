# scripts/credits.tcl — Trigger the real end-credits sequence from anywhere
#
# Usage (in the openMSX TCL console during ACTIVE gameplay):
#   source scripts/credits.tcl
#   credits
#
# This faithfully reproduces `LAB_92af` (0x92AF), the scroll-engine event that
# the game runs after the final boss dies.  It does NOT need a trampoline: the
# main loop's own dispatcher does all the heavy lifting once the flags are set.
#
# How it works (verified against savestates/game-end.oms, sprint 0033):
#
#   E722 = 0xA6F4    ending level-stream pointer (round-0 / logo data).
#                    LAB_40da reads it at 0x40DD to pick the new stage.
#   E701 = 0x00      *old* stage index = 0.  REQUIRED: load_logo_tiles
#                    (0x5C3C, the ZANAC-logo decompressor) only runs from
#                    LAB_412a, which is reached only when BOTH the old stage
#                    (E701) AND the new stage (from E722) are multiples of 8.
#                    The real ending satisfies this because it transitions from
#                    round 8 -> round 0; from mid-game we must force E701=0 or
#                    the logo renders as a garbled multicolour block.
#   E712 = 0x80      target scroll speed = fast ("game beaten" fast scroll).
#   E700 = 0x00      scroll engine back to default mode (LAB_92af tail).
#   E102 bit 5       level_complete -> main loop 0x4085 dispatches to LAB_40da
#                    (fade to black, reset, reload stream via sub_940c, mute
#                    enemies via sub_516c, load logo, ending music).  LAB_40da
#                    clears bit 5 (0x4150) and returns to the main loop.
#   E102 bit 3       end_credits  -> next frame, main loop dispatches to
#                    LAB_46d5 (staff-credits display: flashing names + logo
#                    over the continuing background scroll).
#   E102 bit 2       cleared, mirroring sub_92ca (0x92CA).
#
# Result: screen fades, round-0 terrain scrolls fast, only the (controllable)
# player ship remains, ending music plays, developer names flash and the large
# ZANAC logo appears — exactly the in-game ending.

proc credits {} {
    debug write memory 0xE701 0x00   ;# old stage 0  (old & 7 == 0 -> logo path)
    debug write memory 0xE722 0xF4   ;# ending stream pointer low
    debug write memory 0xE723 0xA6   ;# ending stream pointer high (0xA6F4)
    debug write memory 0xE712 0x80   ;# target scroll speed = fast
    debug write memory 0xE700 0x00   ;# scroll engine default mode

    # E102: set bit 5 (level_complete) + bit 3 (end_credits), clear bit 2.
    set e102 [debug read memory 0xE102]
    debug write memory 0xE102 [expr {($e102 | 0x28) & ~0x04}]

    puts "Credits armed (LAB_92af): fade -> round-0 scroll, ending music, logo."
}
