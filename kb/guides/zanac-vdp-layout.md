# Zanac VDP Layout (Screen 2 / Graphic II)

Derived from `init_vdp_regs` (0x42BA) which writes the inline table at 0x42CF
(`02 82 0E FF 03 77 03 01`) to VDP registers 0–7.
**Fully confirmed** by sprint 0003 live openMSX reads: VDP shadow registers,
VRAM name table, sprite attribute table, and sprite generator table all verified.

---

## VDP Register Settings

| Reg | Value | Meaning |
|-----|-------|---------|
| R0 | 0x02 | M2=1 → Screen Mode 2 (Graphic II); EXTVID=0 |
| R1 | 0x82 | 4/16K=1 (16 KB), BL=0 (display off at init), GINT=0, M1=0, M3=0, SI=1 (16×16 sprites), MAG=0 |
| R2 | 0x0E | PN = 14 → name table at 14 × 0x400 = **0x3800** |
| R3 | 0xFF | CT13=1 → color table at **0x2000**; AND mask = 0x7F (all 3 banks enabled) |
| R4 | 0x03 | PG13=0 → pattern table at **0x0000**; bits 1–0 = 0b11 → all 3 pattern banks active |
| R5 | 0x77 | SA = 0x77 → sprite attribute table at 0x77 × 0x80 = **0x3B80** |
| R6 | 0x03 | SG = 3 → sprite generator table at 3 × 0x800 = **0x1800** |
| R7 | 0x01 | TC = 0 (black), BD = 1 (black border) |

---

## VRAM Map

| Range | Size | Contents |
|-------|------|----------|
| 0x0000–0x17FF | 6144 | Pattern generator table bank 0 (rows 0–7) |
| 0x1800–0x1FFF | 2048 | Sprite generator table (256 × 8 bytes for 8×8; or 64 × 32 bytes for 16×16) |
| 0x2000–0x37FF | 6144 | Color table (3 × 256 × 8 = one CT byte per pixel row per tile; high nibble = FG, low = BG) |
| 0x3800–0x39FF | 512  | Name table (32 × 24 = 768 bytes, 3800–3AFF; first 512 bytes used for rows 0–15) |
| 0x3800–0x3AFF | 768  | Name table full (32 cols × 24 rows = 768 bytes) |
| 0x3B00–0x3B7F | 128  | (unused gap between name table end and SAT) |
| 0x3B80–0x3BFF | 128  | Sprite attribute table (32 sprites × 4 bytes each) |
| 0x3C00–0x3FFF | 1024 | Free / used as secondary display buffer or work area |

> **Note**: the pattern table second bank (rows 8–15) begins at 0x0800 within
> the same 0x0000 base (R4 AND mask = 0b11 enables full 3-bank mode).
> Color table is at 0x2000 (CT13=1, 0xFF mask = no restriction).

---

## HUD VRAM Addresses

From sprint-0002 BIOS-call survey — addresses observed in `render_score_bcd`,
`update_status_bar`, `update_fire_display`, and related routines:

| VRAM addr | Purpose |
|-----------|---------|
| 0x3800–0x3AFF | Name table (full screen, 32×24) |
| 0x3809 | Lives score display start (3 digits) |
| 0x3815 | Top-score display start |
| 0x3839 | HUD left score area |
| 0x3859 | HUD right score area |
| 0x3878 | (second row offset from 0x3818) |
| 0x38B8 | Top-score second row |
| 0x3918 | Current score second row |
| 0x3924 | Bonus/level display area |
| 0x3960–0x396E | Weapon/fire indicator (5 tiles) at 0x396A |
| 0x397A | Fire weapon type display ("FIRE" indicator area) |
| 0x39BB | Shot level digit (0xE10B → "LEVEL" indicator) |
| 0x3A1B | Hi-score digit |
| 0x3ABD | Numeric HUD display |
| 0x3B00–0x3B7F | (gap — unused by name table) |
| 0x3B80–0x3BFF | Sprite attribute table (SAT): 32 sprites × 4 bytes |
| 0x3C00–0x3E3F | Secondary name table or display buffer (level transitions) |

---

## Title Screen Name Table Layout (confirmed, sprint 0003)

At boot/title screen, name table row 0 (0x3800) contains the HUD header.
Live read: `   SCORE          0 TOP   10000    `

| Name table range | Content |
|-----------------|---------|
| 0x3803–0x3807 | "SCORE" label (cyan, tile colour 7) |
| 0x3809–0x380F | Current score (7 digits, light-red colour 9; score=0 → "      0") |
| 0x3811–0x3813 | "TOP" label |
| 0x3815–0x381B | Top score (7 digits; 10000 default → "  10000") |
| 0x38A0–0x39FF | Zanac logo tiles (tile codes 0xB0–0xE6, rows 5–9) |
| 0x3960–0x396F | Row 11: "              A.I.              " |
| 0x39E0–0x39FF | Row 15: "   GAME DESIGNED BY COMPILE     " |
| 0x3A00–0x3A1F | Row 16: "   PRODUCED      BY AII         " |
| 0x3A20–0x3A3F | Row 17: "   PRESENTED     BY PONY INC.   " |
| 0x3A40–0x3A5F | Row 18: "   COPYRIGHT @ 1986 PONY INC.   " |

**Color scheme** (confirmed from color table CT at 0x2000):
- Labels ("SCORE", "TOP", credits): color 7 = Cyan (FG) on transparent BG
- Score digits ('0'–'9'): color 9 = Light red on transparent BG
- Backdrop/border: BD=1 = Black

**Score BCD format** (7-digit field):
- `score_lo` (0xE103): digit pair 1–2 (rightmost)
- `score_mid` (0xE104): digit pair 3–4
- `score_hi` (0xE105): digit pair 5–7 (leftmost, 3 BCD digits)
- Top score: same format in 0xE106–0xE108
- Default top score: `00 10 00` → "0010000" → displayed "  10000" at 0x3815

## Sprite Generator Table (VRAM 0x1800)

| Pattern | VRAM range | Description |
|---------|-----------|-------------|
| 0 | 0x1800–0x181F | All zeros — blank/null sprite |
| 1 | 0x1820–0x183F | Player shot projectile (shot_single / pat10) |
| 2 | 0x1840–0x185F | Asymmetric shape — possible ship fragment |
| 3 | 0x1860–0x187F | Larger symmetric shape — possible player ship or large projectile |

Pattern 1 left half: `00 00 00 0A 15 2B 57 57 57 57 57 2B 15 0A 00 00`
Pattern 1 right half: `00 00 00 E0 10 C8 E4 E4 E4 E4 E4 C8 10 E0 00 00`

## BIOS Shadow Divergence (confirmed, sprint 0003)

**RG1SAV (0xF3E0) diverges from actual VDP R1** after first call to `enable_display`
(0x42E2). The game reads the shadow, toggles the BL bit, and writes to VDP, but does
NOT write back to the shadow. Live: shadow=0x82 (BL=0), actual VDP R1=0xC2 (BL=1).

For accurate VDP register reads: use `debug read_block {VDP regs}` via openMSX,
not the BIOS shadow at 0xF3DF–0xF3E6.

## Sprite Configuration

- **16×16 sprites** (R1 SI=1), **not magnified** (MAG=0).
- Sprite attribute table at **0x3B80** (32 sprites × 4 bytes = 128 bytes).
- Sprite generator table at **0x1800**.
- Pattern address formula for 16×16: `(pattern AND 0xFC) × 8` → offset in SG table.
- Max 4 sprites per horizontal line; Y=208 terminates list.

---

## Screen Mode Activation

After `init_vdp_regs` writes R0–R7, the display is off (R1 BL=0). Routines
`enable_display` (0x42E2) and `disable_display` (0x42D7) toggle the BL bit of
R1 using `rg1sav` (0xF3E0) as the shadow.
