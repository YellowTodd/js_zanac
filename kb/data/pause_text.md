---
address: 0x4E40
end: 0x4E44
kind: data
name: pause_text
confidence: confirmed
sprint: "0063"
tags: [hud, pause, string]
---

# pause_text

The 5 ASCII bytes `"PAUSE"` (`50 41 55 53 45`), blitted to VRAM 0x396A (name
table, status area) by the pause blink logic documented in
[[update_fire_display]] / [[pause_handler]]: every 16 frames the handler
alternates between writing these 5 characters and restoring the saved tiles
from E119, making the PAUSE legend flash while the game is paused.

## See also

[[pause_handler]], [[update_fire_display]].
