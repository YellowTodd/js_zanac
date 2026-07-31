/**
 * PSG sound engine: a native reimplementation of the VBlank-driven,
 * shadow-register sequencer (kb/guides/sound-engine.md).
 *
 *   play_sound_event     0x5189  enqueue event 1..27 into free voice slots
 *   load_sound_event     0x5199  copy 8 header bytes per voice, slot = D*27
 *   psg_sound_tick       0x4E7B  per-frame: sequence, envelope, flush R0-R10
 *   advance_track_stream 0x4F4A  the token grammar (notes/durations/commands)
 *   init_psg_freq_table  0x513F  note -> period
 *
 * Pure JS - no WebAudio here. `tick()` advances one frame and leaves the PSG
 * register image in `regs` (R0..R10); the browser backend turns that into
 * sound, and headless tests can assert on it directly.
 *
 * Note -> period (settles the "outstanding" item in sound-engine.md):
 * 0x513F builds the 0xF200 table as `entry(sem, oct) = base[sem] >> oct` at
 * address `0xF200 + sem*2 + oct*0x19` - the write advances 2 bytes then adds
 * 0x17, so the octave stride is 0x19. With `note = oct*12 + sem + 1`:
 * `period(note) = base[(note-1) % 12] >> ((note-1) / 12 | 0)`.
 */

const EVENT_PTR_TABLE = 0x5234;
const DURATION_TABLE = 0x526c;
const PERIOD_BASE_TABLE = 0x51f0;
const VOICE_SLOTS = 5;
/** Volume-curve selector: a word table; entry n*2 points at curve n's bytes. */
const CURVE_SELECTOR = 0x527d;

/** Voice-config bits (slot[0]). */
const CFG_TONE = 0x01;
const CFG_NOISE = 0x02;
const CFG_BUSY = 0x40;

export class PsgEngine {
  /** @param {import('./assets.js').DataRom} rom */
  constructor(rom) {
    this.rom = rom;
    /** Shadow R0..R10; R7 mixer starts 0xB8 (tones on, noise off). */
    this.regs = new Uint8Array(11);
    this.regs[7] = 0xb8;
    this.voices = Array.from({ length: VOICE_SLOTS }, () => ({
      cfg: 0,
      amp: 0,
      curve: 0,
      transpose: 0,
      tempo: 1,
      channel: 0,
      ptr: 0,
      playFlags: 0,
      subStep: 0,
      duration: 1,
      lastNote: 0,
      tick: 1,
      lastDuration: 1,
      loopCnt: 0,
      noisePeriod: 0,
      curvePhase: 0,
      period: 0,
      // exact ramps (0x4ED3 / 0x4F0D): fractional accumulators stepping on
      // 8-bit carry
      envRate: 0,
      envAcc: 0,
      envTarget: 0,
      slideRate: 0,
      slideAcc: 0,
      slideShift: 0,
      slideDir: 0,
    }));
  }

  periodForNote(note, transpose) {
    const n = note + transpose - 1;
    if (n < 0 || n >= 120) return 0;
    const base =
      this.rom.byte(PERIOD_BASE_TABLE + (n % 12) * 2) |
      (this.rom.byte(PERIOD_BASE_TABLE + (n % 12) * 2 + 1) << 8);
    return base >> ((n / 12) | 0);
  }

  /** `play_sound_event` / `load_sound_event`. */
  playEvent(n) {
    if (n < 1 || n > 27) return;
    let p = this.rom.word(EVENT_PTR_TABLE + 2 * n);
    let count = this.rom.byte(p++);
    while (count-- > 0) {
      const d = this.rom.byte(p);
      const v = this.voices[d % VOICE_SLOTS];
      v.cfg = this.rom.byte(p + 1) | CFG_BUSY;
      v.amp = this.rom.byte(p + 2);
      v.curve = this.rom.byte(p + 3);
      v.transpose = ((this.rom.byte(p + 4) << 24) >> 24);
      v.tempo = this.rom.byte(p + 5) || 1;
      v.channel = this.rom.byte(p + 6) % 3;
      v.ptr = this.rom.byte(p + 7) | (this.rom.byte(p + 8) << 8);
      p += 9;
      // sequencing state reset so the first token is fetched immediately
      v.tick = 1;
      v.subStep = 0;
      v.duration = 1;
      v.lastDuration = 1;
      v.lastNote = 0;
      v.period = 0;
      v.playFlags = 0;
      v.envRate = 0;
      v.envAcc = 0;
      v.slideRate = 0;
      v.slideAcc = 0;
    }
  }

  /**
   * `fade_music_out` (0x5211). Not a stop: it walks the **three music voice
   * slots** (0xE20C, stride 0x1B) and arms each one's volume envelope -
   * `SET 5,(IX+8)` is the VOL_ENV active flag, `(IX+0x16) = 8` the target,
   * `(IX+0x14) = 0x10` the rate, `(IX+0x15) = 0` the accumulator - so the
   * tune ramps down and keeps playing until it does. Used when a base opens
   * and when its clock runs out.
   */
  fadeMusic() {
    for (let i = 0; i < 3 && i < this.voices.length; i++) {
      const v = this.voices[i];
      v.playFlags |= 0x20;
      v.playFlags &= ~0x02;
      v.envTarget = 0x08;
      v.envRate = 0x10;
      v.envAcc = 0;
    }
  }

  /**
   * `mute_sound` (0x5208) / `restore_sound` (0x520E): the pause mute. The ROM
   * pokes 0xE200, which the driver reads as "hold every channel off". The
   * sequencer keeps running underneath, so unpausing resumes the tune
   * mid-phrase instead of restarting it.
   *
   * @param {boolean} on
   */
  setMuted(on) {
    this.muted = !!on;
  }

  /** `stop_all_sound` (0x516C): silence every voice and the mixer. */
  stopAll() {
    for (const v of this.voices) v.cfg = 0;
    this.regs[7] = 0xbf;
    this.regs[8] = this.regs[9] = this.regs[10] = 0;
  }

  /** One frame (`psg_sound_tick`). */
  tick() {
    for (const v of this.voices) {
      if ((v.cfg & CFG_BUSY) === 0) continue;
      if (--v.tick <= 0) {
        v.tick = v.tempo;
        if (++v.subStep >= v.duration) this.advanceStream(v);
      }
      // Volume-envelope ramp (0x4ED3), exact: the rate is a fractional
      // accumulator - a step fires only when the 8-bit add carries - and the
      // ramp is FADE-DOWN ONLY: amp decrements until it equals the target,
      // which sets play-flag bit 1 (read by JUMP_IF_ENV).
      if (v.playFlags & 0x20) {
        const sum = v.envAcc + v.envRate;
        v.envAcc = sum & 0xff;
        if (sum > 0xff) {
          if (v.amp === v.envTarget) v.playFlags |= 0x02;
          else {
            v.playFlags &= ~0x02;
            v.amp = (v.amp - 1) & 0xff;
          }
        }
      }
      // Pitch slide (0x4F0D), exact: on each carried step the period moves by
      // (period >> shift) - a geometric glide, not linear. Play-flag bit 6
      // selects subtract (pitch up); overflow past 0x0FFF or underflow clamps
      // the period to 0, silencing the channel.
      if ((v.playFlags & 0x80) && v.slideShift) {
        const sum = v.slideAcc + v.slideRate;
        v.slideAcc = sum & 0xff;
        if (sum > 0xff && v.period) {
          const delta = v.period >> v.slideShift;
          if (v.slideDir) {
            v.period -= delta;
            if (v.period < 0) v.period = 0;
          } else {
            v.period += delta;
            if (v.period >= 0x1000) v.period = 0;
          }
        }
      }
    }
    this.flush();
  }

  /** `advance_track_stream` (0x4F4A). */
  advanceStream(v) {
    const rom = this.rom;
    for (let guard = 0; guard < 64; guard++) {
      const b = rom.byte(v.ptr++);

      if (b <= 0x7f) {
        // note; optional duration token follows
        let dur = v.lastDuration;
        const nb = rom.byte(v.ptr);
        if (nb >= 0xdf) {
          v.ptr++;
          dur = this.durationToken(v, nb);
        }
        this.setNote(v, b, dur);
        return;
      }
      if (b >= 0xdf) {
        this.setNote(v, v.lastNote, this.durationToken(v, b)); // replay
        return;
      }

      switch (b) {
        case 0x80: // JUMP
          v.ptr = rom.word(v.ptr);
          break;
        case 0x81: {
          // LOOP
          const target = rom.word(v.ptr);
          v.ptr += 2;
          if (--v.loopCnt & 0xff) v.ptr = target;
          break;
        }
        case 0x82: // END
          v.cfg = 0;
          this.silenceChannel(v.channel);
          return;
        case 0x83: {
          // JUMP_IF_ENV (jump while the ramp has not reached its target)
          const target = rom.word(v.ptr);
          v.ptr += 2;
          if ((v.playFlags & 0x02) === 0) v.ptr = target;
          break;
        }
        case 0x84:
          v.curve = rom.byte(v.ptr++);
          v.curvePhase = 0;
          break;
        case 0x85: {
          const nn = (rom.byte(v.ptr++) << 24) >> 24;
          v.transpose = nn === 0 ? 0 : v.transpose + nn;
          break;
        }
        case 0x86: {
          const nn = (rom.byte(v.ptr++) << 24) >> 24;
          v.amp = Math.max(0, Math.min(15, v.amp + nn));
          break;
        }
        case 0x87:
          this.playEvent(rom.byte(v.ptr++)); // track chaining (ev7 -> ev1)
          break;
        case 0x88:
          v.loopCnt = rom.byte(v.ptr++);
          break;
        case 0x89:
          v.noisePeriod = rom.byte(v.ptr++);
          break;
        case 0x8a: {
          // IDX_TRANSPOSE: per-loop-iteration pitch offset
          const table = rom.word(v.ptr);
          v.ptr += 2;
          const dt = (rom.byte(table + ((v.loopCnt - 1) & 0xff)) << 24) >> 24;
          v.transpose += dt;
          break;
        }
        case 0x8b: {
          // VOL_ENV target, rate -> the 0x4ED3 fade-down ramp
          v.envTarget = rom.byte(v.ptr++);
          v.envRate = rom.byte(v.ptr++);
          v.envAcc = 0;
          v.playFlags &= ~0x02;
          v.playFlags |= 0x20;
          break;
        }
        case 0x8c: {
          // PITCH_SLIDE ff, rr -> the 0x4F0D geometric glide
          const ff = rom.byte(v.ptr++);
          v.slideShift = ff & 0x7f;
          v.slideDir = ff >> 7;
          v.slideRate = rom.byte(v.ptr++);
          v.slideAcc = 0;
          v.playFlags |= 0x80;
          break;
        }
        default:
          // 0x8D-0xDE: past the command table; treat as END to fail safe
          v.cfg = 0;
          this.silenceChannel(v.channel);
          return;
      }
    }
    v.cfg = 0; // runaway stream
  }

  durationToken(v, t) {
    let d;
    if (t === 0xdf) d = this.rom.byte(v.ptr++);
    else d = this.rom.byte(DURATION_TABLE + (t - 0xe0));
    v.lastDuration = d || 1;
    return v.lastDuration;
  }

  setNote(v, note, duration) {
    v.lastNote = note;
    v.duration = duration;
    v.subStep = 0;
    v.curvePhase = 0;
    v.period = note === 0 ? 0 : this.periodForNote(note, v.transpose);
  }

  silenceChannel(ch) {
    this.regs[8 + ch] = 0;
  }

  /** `apply_amp_curve` (0x5099): per-frame amplitude from the curve tables. */
  curvedAmp(v) {
    if (v.curve === 0) return v.amp & 0x0f;
    const table = this.rom.word(CURVE_SELECTOR + v.curve * 2);
    let phase = v.curvePhase;
    v.curvePhase = (v.curvePhase + 1) & 0xff;
    let c = this.rom.byte(table + phase);
    if (c & 0x80) {
      phase--;
      v.curvePhase = phase + 1;
      c = this.rom.byte(table + phase);
    }
    const atten = (~c + 0x10) & 0xff; // = 15 - c for c <= 0x0F
    const out = (v.amp & 0x0f) - atten;
    return out > 0 ? out : 0;
  }

  /** Output stage: rebuild R0..R10 from the live voices. */
  flush() {
    let mixer = 0xbf; // all off (tone bits 0-2, noise bits 3-5, active low)
    const owned = [null, null, null];
    for (const v of this.voices) {
      if ((v.cfg & CFG_BUSY) === 0) continue;
      owned[v.channel] = v; // later slots win the channel, as the flush loop does
    }
    for (let ch = 0; ch < 3; ch++) {
      const v = owned[ch];
      if (!v || v.period === 0) {
        this.regs[8 + ch] = 0;
        continue;
      }
      this.regs[2 * ch] = v.period & 0xff;
      this.regs[2 * ch + 1] = (v.period >> 8) & 0x0f;
      this.regs[8 + ch] = this.curvedAmp(v);
      if (v.cfg & CFG_TONE) mixer &= ~(1 << ch);
      if (v.cfg & CFG_NOISE) {
        mixer &= ~(8 << ch);
        this.regs[6] = v.noisePeriod & 0x1f;
      }
    }
    this.regs[7] = mixer;
  }
}
