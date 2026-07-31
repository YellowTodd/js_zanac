/**
 * Sound front-end: the game-facing event API plus the PSG sequencer.
 *
 * `playEvent`/`stopAll` mirror `play_sound_event` (0x5189) and
 * `stop_all_sound` (0x516C). The event log stays for headless tests; the
 * register image in `engine.regs` is what the WebAudio backend consumes.
 */

import { PsgEngine } from './psg.js';

export class Sound {
  /** @param {import('./assets.js').DataRom} [rom] */
  constructor(rom) {
    /** @type {number[]} events requested since the last drain */
    this.log = [];
    this.engine = rom ? new PsgEngine(rom) : null;
  }

  /** `play_sound_event` (0x5189). */
  playEvent(id) {
    this.log.push(id);
    if (this.engine) this.engine.playEvent(id);
  }

  /** `mute_sound` (0x5208) / `restore_sound` (0x520E). */
  setMuted(on) {
    if (this.engine) this.engine.setMuted(on);
  }

  /** `fade_music_out` (0x5211): ramp the three music voices down. */
  fadeMusic() {
    if (this.engine) this.engine.fadeMusic();
  }

  /** `stop_all_sound` (0x516C). */
  stopAll() {
    this.log.push(0);
    if (this.engine) this.engine.stopAll();
  }

  /** Once per frame, from the driver. */
  tick() {
    if (this.engine) this.engine.tick();
  }

  drainLog() {
    const log = this.log;
    this.log = [];
    return log;
  }
}
