# VDP — TMS9918A Reference

Source: `xtra/vdp-manual.txt` (Sean Young, v0.4.2, September 2002).
All information here is `confirmed` from the authoritative hardware manual.

---

## I/O Ports (MSX mapping)

| Port | Direction | Purpose |
|------|-----------|---------|
| 0x98 | R/W | VRAM data (read: read-ahead buffer; write: store to VRAM) |
| 0x99 | Read | VDP status register S#0 |
| 0x99 | Write | VRAM address setup OR control register write (two-byte sequence) |

Port addresses are stored in ROM at:
- **0x0006** (`vdp_dr`) — data read port (0x98)
- **0x0007** (`vdp_dw`) — data write port (0x98)

`vdp_write_byte_di` (0x5BFC) reads the port number from 0x0007 via `LD BC,(0x0007)`.

---

## Control Registers R0–R7

```
Reg  Bit  7    6     5     4     3     2     1     0
 0        -    -     -     -     -     -     M2  EXTVID
 1      4/16K  BL  GINT    M1    M3    -     SI   MAG
 2        -    -     -     -   PN13  PN12  PN11  PN10
 3      CT13  CT12  CT11  CT10  CT9   CT8   CT7   CT6
 4        -    -     -     -     -   PG13  PG12  PG11
 5        -  SA13  SA12  SA11  SA10   SA9   SA8   SA7
 6        -    -     -     -     -   SG13  SG12  SG11
 7      TC3   TC2   TC1   TC0   BD3   BD2   BD1   BD0
```

| Bit | Meaning |
|-----|---------|
| M1, M2, M3 | Screen mode select (see modes below) |
| EXTVID | Enable external video input |
| 4/16K | Select 16 KB VRAM (no effect on MSX1 — always 16 KB) |
| **BL** | **Blank screen if RESET (0); sprite system inactive. Display on = 1.** |
| **GINT** | **Generate VBLANK interrupt if SET (1). Cleared bit → no interrupts.** |
| SI | Sprite size: 0 = 8×8, 1 = 16×16 |
| MAG | Sprite magnify (1 = sprites drawn 2×2 pixels each) |
| PN13–PN10 | Name table base: addr = PN × 0x400 |
| CT13–CT6 | Color table base (Mode 2: CT13 only; bits 6–0 = AND mask) |
| PG13–PG11 | Pattern table base (Mode 2: PG13 only; bits 1–0 = bank AND mask) |
| SA13–SA7 | Sprite attribute table base: addr = SA × 0x80 |
| SG13–SG11 | Sprite generator table base: addr = SG × 0x800 |
| TC3–TC0 | Text foreground colour (Mode 1 only) |
| BD3–BD0 | Border/backdrop colour (all modes) |

Register mirrors in RAM: **RG0SAV–RG7SAV at 0xF3DF–0xF3E6**.
`vdp_int_disable` (0x42ED) clears GINT (R1 bit 5) via RG1SAV;
`vdp_int_enable` (0x42F8) sets it. Both call WRTVDP (0x0047).

---

## Status Register S#0 (read port 0x99)

```
Bit  7     6    5    4   3   2   1   0
     INT   5S   C   FS4 FS3 FS2 FS1 FS0
```

| Bit | Meaning |
|-----|---------|
| **INT** | Set at end of active display (VBLANK). Cleared on read. |
| **5S** | Fifth-sprite (illegal sprite) detected on a line |
| **C** | Sprite-to-sprite collision detected anywhere on screen |
| FS4–FS0 | First illegal sprite number (valid only if 5S set) |

Mirror in RAM: **STATFL at 0xF3E7** (copied by BIOS ISR).
**Reading S#0 also clears INT and C**, so the ISR must always read it.

---

## Screen Modes

| M1 | M2 | M3 | MSX BASIC | Resolution | Sprites |
|----|----|----|-----------|------------|---------|
|  0 |  0 |  0 | SCREEN 1 (Graphic I)  | 32×24 chars | ✓ |
|  1 |  0 |  0 | SCREEN 0 (Text)       | 40×24 chars, 6px wide | ✗ |
|  0 |  1 |  0 | SCREEN 2 (Graphic II) | 32×24 chars, 3 pattern banks | ✓ |
|  0 |  0 |  1 | SCREEN 3 (Multicolor) | 32×24 cells, each 4×4px | ✓ |

### Mode 2 (SCREEN 2 / Graphic II) — used by Zanac

- **Name table (PN)**: 32×24 = 768 bytes. Each byte indexes a pattern/colour tile.
- **Pattern table (PG)**: 3 × 256 × 8 = 6144 bytes. Rows 0–7 use bank 0, rows 8–15 use bank 1, rows 16–23 use bank 2. PG13 selects 0x0000 or 0x2000. R4 bits 1–0 are an AND mask over the high bits of the character index.
- **Color table (CT)**: 3 × 256 × 8 = 6144 bytes. One byte per pixel-row per character. High nibble = foreground, low nibble = background (0 = transparent = BD color). CT13 selects 0x2000 or 0x0000; R3 bits 6–0 are AND mask.
- **Sprite attribute table (SA)**: 32 sprites × 4 bytes = 128 bytes. addr = SA × 0x80.
- **Sprite generator table (SG)**: addr = SG × 0x800.

---

## VRAM Address Protocol

Two bytes must be written to port 0x99 in sequence (interrupts disabled between them):

```
Byte 0: A7–A0        (low 8 bits of VRAM address)
Byte 1: 0  R/W  A13 A12 A11 A10 A9 A8
         └─ R/W: 0 = read setup, 1 = write setup
```

- **Write setup** (R/W = 1): sets r/w address to A13–A0.
- **Read setup** (R/W = 0): reads VRAM[A13–A0] into the read-ahead buffer, sets r/w address to A+1.

After each port-0x98 access the address auto-increments. Wraps at 0x3FFF.

**Interrupts MUST be disabled** while writing the two-byte sequence to port 0x99; any intervening VDP access (including the status register read in the ISR) resets the internal pair-pending flag and corrupts the write.

---

## Interrupt Mechanism

1. At the end of raster line 192 (bottom of active display), VDP sets S#0 bit 7 (INT).
2. If GINT (R1 bit 5) is also set, VDP asserts INT line → Z80 interrupt.
3. ISR reads S#0 (port 0x99) → clears INT bit → de-asserts INT line.
4. If GINT is cleared while INT is already set, the interrupt line goes high again immediately (no spurious repeat). Setting GINT while INT is set fires the interrupt immediately.

---

## Sprite System

- **32 sprites** total; max **4 per horizontal line** (others are "illegal" = not drawn).
- Sprite attribute entry (4 bytes): Y, X, pattern#, colour+EC.
- Y = 208 terminates the sprite list (sprites after are not drawn).
- Y = 0 → displayed on pixel line 1 (Y coordinate is 0-based from line 1).
- EC bit (colour byte bit 7): shift sprite 32 pixels to the left (early clock).
- Colour 0 = transparent sprite (pattern still counts for collision and illegality).
- 8×8 sprites: pattern × 8 = offset in SG table.
- 16×16 sprites: (pattern AND 0xFC) × 8 = offset; 16 bytes left half, 16 bytes right half.
- Collision (C bit): any two non-transparent sprite pixels overlap anywhere on screen.

---

## Colours (TMS9918A NTSC palette)

| # | Name | R | G | B |
|---|------|---|---|---|
| 0 | Transparent | — | — | — |
| 1 | Black | 0 | 0 | 0 |
| 2 | Medium green | 33 | 200 | 66 |
| 3 | Light green | 94 | 220 | 120 |
| 4 | Dark blue | 84 | 85 | 237 |
| 5 | Light blue | 125 | 118 | 252 |
| 6 | Dark red | 212 | 82 | 77 |
| 7 | Cyan | 66 | 235 | 245 |
| 8 | Medium red | 252 | 85 | 84 |
| 9 | Light red | 255 | 121 | 120 |
| A | Dark yellow | 212 | 193 | 84 |
| B | Light yellow | 230 | 206 | 128 |
| C | Dark green | 33 | 176 | 59 |
| D | Magenta | 201 | 91 | 186 |
| E | Gray | 204 | 204 | 204 |
| F | White | 255 | 255 | 255 |
