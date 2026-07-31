ZANAC SPRITE NAMES - from https://strategywiki.org/wiki/Zanac

A "complement" sprite (abbrev. `_compl`) is a second overlapping sprite drawn
at the same position to add a second color, working around the MSX1 limitation
of one color per sprite. The complement is always color 0x81 (black, EC bit set)
or a dark tint, creating depth or shadow illusion. It is distinct from the SAT
shadow buffer (0xE000).

00    - empty
01    - `power chip` (weapon upgrade)
02    - comet
03    - target
04    - snowflake
05    - small star
06    - `light bar` (projectile)
07    - `lead` (small bullet)
08    - medium circle
09    - large circle
10-12 - shot: single, double and triple
13    - `super hard bolt` (spike-like projectile)
14-15 - `player ship` + complement
16-17 - plane + complement (enemy)
18-21 - `loga` 2x + complement 2x (opener enemy, animated)
22-23 - `duster` + complement (meteor-like enemy)
24-25 - `teruzo` + complement (ball-like enemy)
26-28 - `sig`: triple, double and single (missile)
29-32 - `luster` 2x + complement 2x (tank-like enemy, animated)
33-42 - `veybar` 5x + complement 5x (glider-like enemy, animated)
43-50 - spinner 4x + complement 4x (enemy, animated)
51-52 - stealth + complement (enemy)
53-54 - box + complement
55-58 - `umber` 2x + complement 2x (squid-like enemy, animated)
59-61 - `degid`: left, right and complete (enemy)
62-63 - `sart` + complement
