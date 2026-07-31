# spawn_type.tcl — inject a numbered entity type into a free enemy slot.
#
# Load in the openMSX console:
#   source /path/to/scripts/spawn_type.tcl
#
# Then call:
#   spawn_type 26          ;# type 26 at default Y=100 X=120
#   spawn_type 7 80 160    ;# custom initial position
#
# The player is made invincible before the spawn so the game keeps running.
# The type is written WITHOUT the active flag (bit 7), which causes entity_dispatch
# to run the handler's init path on the very next dispatch cycle.

# ── Entity table constants ────────────────────────────────────────────────────
set ::_ENT_BASE      0xE300
set ::_ENT_SLOT_SIZE 32          ;# bytes per slot
set ::_ENT_FIRST     5           ;# first enemy slot index (slots 0-4 = player/shots)
set ::_ENT_LAST      24          ;# last usable probe slot

# ── Helpers (prefixed to avoid polluting the global namespace) ────────────────

proc _spawn_invincible {} {
    poke 0xe305 [expr {[peek 0xe305] | 128}]   ;# set +0x05 bit7 = invincible flag
    poke 0xe31b 255                            ;# reload invincibility timer
}

# Return the base address of the first free enemy slot, or -1 if all occupied.
proc _spawn_free_slot {} {
    global _ENT_BASE _ENT_SLOT_SIZE _ENT_FIRST _ENT_LAST
    for {set i $_ENT_FIRST} {$i <= $_ENT_LAST} {incr i} {
        set addr [expr {$_ENT_BASE + $i * $_ENT_SLOT_SIZE}]
        if {[peek $addr] == 0} {
            return $addr
        }
    }
    return -1
}

# Zero all 32 bytes of a slot so the handler starts from a clean state.
proc _spawn_clear {addr} {
    global _ENT_SLOT_SIZE
    for {set i 0} {$i < $_ENT_SLOT_SIZE} {incr i} {
        poke [expr {$addr + $i}] 0
    }
}

# ── Main entry point ──────────────────────────────────────────────────────────

proc spawn_type {type_id {y 100} {x 120}} {
    global _ENT_BASE _ENT_SLOT_SIZE

    _spawn_invincible

    set slot [_spawn_free_slot]
    if {$slot < 0} {
        error "spawn_type: no free enemy slot available (slots 5-24 all occupied)"
    }

    _spawn_clear $slot

    poke [expr {$slot + 1}] $y       ;# +0x01  Y position
    poke [expr {$slot + 2}] $x       ;# +0x02  X position
    poke $slot $type_id              ;# +0x00  type, bit7 clear → init on next dispatch

    set idx [expr {($slot - $_ENT_BASE) / $_ENT_SLOT_SIZE}]
    puts "spawn_type: type $type_id → slot $idx (addr 0x[format %04X $slot])  Y=$y X=$x"
}
