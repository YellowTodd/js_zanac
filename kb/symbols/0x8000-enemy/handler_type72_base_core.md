---
address: 0x8983
end: 0x8a15
kind: routine
name: handler_type72_base_core
confidence: confirmed
inputs:  { IX: "entity slot" }
outputs: {}
clobbers: [AF, BC, DE, HL, IY]
calls:   [0x4898, 0x44b0, 0x8a26, 0x5189, 0x48d0]
called_by: [0x445f]
tags: [entity, enemy, base, core, orb, warp, pickup, objective]
sprint: "0059"
---

# handler_type72_base_core

**Type 72 — the floating power/warp ORB** (spawned by an idol; see
[[idol-warp-orbs]]). Rises slowly into view (pattern 0x24 = large circle) with a
2-phase animation and runs down a **yellow→black** life counter `(IX+0x1E)`
(init 4). Its effect fires on **player touch** (collision vs the player slot,
0x44B0 → the code below runs only after the touch cleared bit 7):

- `(IX+0x1E) != 0` — **YELLOW** orb → `explode_enemies` (0x8A26) = **kill all
  enemies** + SFX 0x13, then despawn.
- `(IX+0x1E) == 0` — **BLACK** orb → **warp**: `E722 = (IX+0x1C/1D)` (a stream
  pointer inherited from the idol table at 0xE720), set round-clear flag
  0xE102 bit 5 → `level_complete_handler` → `resolve_round_from_ptr` → `E701` =
  destination round. Live-confirmed sprint 0059.

> **Correction (0059):** previously framed as a "base core whose destruction
> advances round progress". The bit-5 path is the **warp**, not a plain advance;
> the two branches are the two orb effects. The per-round warp destinations are
> catalogued in [[idol-warp-orbs]]. (Was labelled "slow-rise animated"; raw DB
> block 0x8983–0x8a15 disassembled sprint 0052, ROM byte-identical. Anim data in
> [[base_core_anim]] 0x8a16.)

```
8983  BIT 7,(IX+0x00) / JR NZ,0x89bb
8989  SET 7 / LD (IX+0x09),0xff / (IX+0x08),0xf8   ; rise (vy ≈ -0.03)
8995  LD (IX+0x0c),0x05                              ; bflags = Y + anim
8999  LD (IX+0x11),0x16 / (IX+0x12),0x8a             ; anim ptr = base_core_anim (0x8a16)
89a1  (IX+0x0f)=0 (IX+0x10)=4 (IX+0x0d)=1 (IX+0x0e)=4 ; 4-frame anim
89b1  (IX+0x1e)=4 / (IX+0x1f)=(IX+0x18)
; active (0x89bb): countdown via +0x1b/+0x1e/+0x1f; at +0x1f==0x46 → entity_clear
89d3  (switch to 2nd anim: +0x11=0x1e, +0x08=0xf0)
89df  CALL 0x4898 / BIT 7 / RET Z
89e7  CALL 0x44b0 / BIT 7 / RET NZ                   ; hit-sub: survived → return
; destroyed:
89ef  LD A,0x81 / LD (0xe300),A                       ; reinit player slot type
89f4  LD A,(IX+0x1e) / AND A / JR Z,0x8a05                ; yellow? (!=0) : black (==0)
89fa  CALL 0x8a26 / LD A,0x13 / CALL 0x5189 / JP 0x48d0  ; YELLOW: kill-all-enemies + SFX
8a05  LD HL from +0x1c/1d / LD (0xe722),HL               ; BLACK: E722 = warp destination (stream ptr)
8a0e  LD HL,0xe102 / SET 5,(HL) / JP 0x48d0              ; set level_complete → warp to that round
```

> **Naming (0068):** name **kept** in the naming-consistency pass. The
> systematic `handler_typeNN_` scheme and the type-72 designation are correct;
> the 0059 orb/warp finding was a *behaviour* correction (above), not a name
> misnomer. See [[naming-conventions]].

## Related

[[idol-warp-orbs]] (full mechanic + per-round warp catalogue),
[[handler_type70_wide_structure]] (the idol that spawns this orb, sets +0x1c/1d),
[[base_core_anim]] (0x8a16), [[explode_enemies]] (0x8a26), `data_e102`
(round-progress flags, [[K-game-flow-state-machine]]), [[entity_jump_table]] (72).
