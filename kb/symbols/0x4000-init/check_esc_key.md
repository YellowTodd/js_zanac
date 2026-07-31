---
address: 0x43D2
end: 0x43D9
kind: routine
name: check_esc_key
confidence: confirmed
inputs: {}
outputs:
  ZF: "Z=1 if ESC is held (row 7 bit 2 low), Z=0 otherwise"
clobbers: [AF]
calls: [BIOS:SNSMAT]
called_by: [0x424C, 0x476C]
tags: [keyboard, title-screen, input]
sprint: "0041"
---

# check_esc_key

## Summary

Reads keyboard **row 7** via SNSMAT and tests **bit 2 = ESC**; returns `Z=1`
when ESC is held (SNSMAT is active-low, so a pressed key reads 0). Formerly
mis-named `check_start_key` with a "SPACE" note — it does **not** read SPACE
(SPACE is row 8 bit 0); it reads ESC.

Used as the ESC modifier in two places:
- `title_screen_init` (0x424C) — ESC held while starting ⇒ skip the `E701 = 1`
  reset, so the game **continues from the last round** (and reaches the secret
  round 0 if E701 was left 0 by a warp death). See [[J-title-screen]],
  [[M-secrets-and-warps]].
- credits loop (0x476C) — ESC ⇒ return to the title screen.

## Analysis (source 0x43D2–0x43D9)

```
43D2  LD A,0x07          ; select keyboard row 7
43D4  CALL 0x0141        ; SNSMAT → A = row-7 matrix byte (active-low)
43D7  BIT 2,A            ; row 7 bit 2 = ESC
43D9  RET                ; Z=1 ⇔ ESC pressed
```

> **BIOS-label note:** `0x0141` is **SNSMAT** (the disasm earlier showed
> `sub_0141`). Verified against `kb/symbols/0x0000-bios/bios_snsmat.md`.

## Confirmation (sprint 0040, live)

- **Key mapping confirmed live** (`tools/trace_check_esc.py` / keymatrix probe):
  at the idle title, `keymatrix` row 7 = `0xFF` with nothing pressed and `0xFB`
  (bit 2 clear) with ESC down — i.e. **ESC = row 7 bit 2**.
- The instruction sequence is ROM-verified (redisasm), and `SNSMAT` with `A=7`
  is the documented "read matrix row 7" BIOS contract.
- The downstream branch is in `title_screen_init`: `PUSH AF` (0x424F) saves the
  Z flag across `init_screen_mode`, `POP AF` (0x4253), then `JR Z,0x425A`
  (0x4254) skips `LD (IX+1),1` (E701 = round 1) when ESC was held. `scripts/warp.tcl`
  exploits this E701 path in practice.

> Early-boot caveat: a `BIT 2,A` breakpoint during the boot-time call returns an
> unsettled SNSMAT value (the keyboard port isn't stable that early); the mapping
> reads cleanly at idle, which is why the keymatrix probe is the authoritative
> check.
