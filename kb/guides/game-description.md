# Game description

When the ROM starts, the `title screen` is shown:

1. First the company names and 1986 year are shown
2. An animated Zanac logo enters the screen, while the `title music` plays
3. Then the logo stays in place and the game waits for the **SPACE** key to start

When the game play starts, it shows the `game screen` and begins at the first stage, called `round 1`. The player starts with 3 lives and the `intro music` begins. After a while, the `main music` keeps repeating.

The player uses the **SHIFT** key to shot the normal `shot`. The `shot` starts at `level` 0, which is a single shot. After getting a `power chip`, the `shot` `level` increases to 1 single fast, 2 double, 3 double fast, 4 triple and 5 triple fast.

The player can also press the **Z** key to shoot the main `fire` weapon (numbered from 0 to 7). It starts with type 0 at beginning of the game play or player death. The **SPACE** key shoots both the current `shot` and `fire`.

The behaviour of each `fire` type is different. Fire 0 has infinite shots, where other fire weapons can be limited ammunition, limited number of enemy kills, limited time or (for the force shield provided by `fire` 2) limited number of collisions with enemies. They are *probably* restricted to one shot on screen at a time. The `fire` limits are shown on screen below the `fire` number indicator. Collecting the same `fire` number restarts the limits; collecting a different number switches to a new `fire`. The `fire` types are:

0 – "All-Range Cannon": fires omnidirectionally in the direction of motion (upward when still); destroys ground objects; infinite use; the default fire.

1 – "Straight Crasher": slow forward-piercing shot; destroys bullets and ground objects; ammo-limited.

2 – "Field Shutter": a forward barrier that blocks bullets, projectiles and enemies; depletes on contact (limite durability). Taking it raises ALC significantly, making the game harder.

3 – "Circular": orbs rotating around the ship; destroys bullets, projectiles and enemies; time-limited.

4 – "Vibrator": horizontally-vibrating shots; slow forward travel but destroys bullets and ground; limited durability per shot.

5 – "Rewinder": boomerang-like piercing shots in front of the ship.

6 – "Plasma Flash": a screen-clearing bomb; hitting an bullet/projectile/enemy with it destroys all aerial enemies; very low ammo.

7 – "High Speed": fast forward/diagonal piercing shots; time-limited. Considered the strongest practical weapon because of the narrow screen.

The `player ship` dodges `bullets` and projectiles, and shoots at the enemies. The background keeps scrolling at constant velocity. The user can also destroy ground constructions, and a special type provide floating upgrades that when collected change to different weapons.

The use can also shoot a floating `box`, which will disappear, either dropping nothing, three `bullets`, or a `power chip`.

When the use reaches a ground `base`, the scrolling will decelerate and then stop. The base will open and close animated eyes which will shoot more `bullets` and projectiles at the player, until destroyed. After the base is defeated the `main music` stops, a loud `explosion` is heard and there is a brief moment of silence. Then the `main music` starts again and the scrolling starts to accelerate, until the formal scroll velocity is reached.

After the player looses his last life and the player ship disappears, a **game over** message is shown, and the `game over music` plays. After a moment of silence the game goes into the `title screen` again.

The background have small black-and-white `idol` constructions which can be shot with both the normal `shot` and the special `fire` weapons. It cannot be destroyed, but after many hits the `idol` will release a floating `yellow orb`. If this orb is touched by the player it will kill all enemies instantly. Some specific "smiling" idols release a special `warp orb`: it functions as a normal `yellow orb`, but if they are not collected after some time, then it will turn into a black orb. Upon touching this `warp orb` the player will teleported to the start of a specific round, even an earlier one.
