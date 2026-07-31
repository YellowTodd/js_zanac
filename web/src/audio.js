/**
 * WebAudio backend: turns the PSG register image into sound.
 *
 * PSG tone frequency = 1789772.5 / (16 * period); volumes are the 4-bit
 * amplitude fields mapped through the AY's measured DAC (`AY_DAC`). Must be
 * constructed after a user gesture.
 *
 * Two things about the AY-3-8910 make the difference between "there is some
 * noise" and Zanac's actual percussion, and the first version of this file got
 * both wrong:
 *
 * 1. **The noise source is not white noise.** It is a 17-bit LFSR whose output
 *    is a two-level square at full amplitude, clocked at `clock / (16 * R6)`,
 *    so R6 sets its pitch - a low rumble at R6 = 31, a bright hiss at R6 = 1.
 *    Uniform white noise costs about 5 dB on its own (a uniform sample has RMS
 *    1/sqrt(3) where a square has 1) and throws the pitch away as well.
 *
 * 2. **Tone and noise on one channel are AND-ed, not added.** Each channel has
 *    a single DAC; the mixer gates it with the tone square AND the noise
 *    square. Zanac leans on this: its explosion (event 18) runs channel C with
 *    both enabled and sweeps the tone period 3648 -> 489, which chops the noise
 *    at 30 -> 229 Hz. Summing the two instead puts a clean square at full level
 *    next to the noise, and that square is what you end up hearing.
 *
 * The AND is built from an audio-rate multiply. With `a` the tone square in
 * {-1,+1} and `n` the noise bit in {0,1}, `AND(a, n) = a*n + n - 1`, so the
 * graph per channel is a gain node fed by the oscillator whose own gain is
 * driven by the noise (that is `a*n`), plus the noise, minus a DC of one. The
 * noise-only case is `2n - 1` through the same two nodes.
 *
 * The LFSR is baked once into a buffer at one step per sample and then
 * repitched with `playbackRate`, which keeps the sequence bit-exact. The
 * buffer is exactly one LFSR period long, so the loop point is seamless.
 */

const PSG_CLOCK = 1789772.5;
/** 2^17 - 1: the AY noise LFSR's period, and so the noise buffer's length. */
const NOISE_PERIOD = 131071;
/** Shared amplitude scale, so noise and tone match at equal register values. */
const CHANNEL_GAIN = 0.33;
/**
 * The AY-3-8910's 16-level DAC, measured and normalised to 1.0 at level 15.
 *
 * It is close to logarithmic and falls away far faster than the `(v/15)^2`
 * curve this file used to approximate it with - level 8 is 0.169, not 0.284,
 * which is 4.5 dB. Zanac's sequencer spends most of its time below full
 * volume (its per-slot decay curves walk the amplitude down step by step), so
 * the square law was holding every tail and every quiet note up several dB and
 * flattening the mix.
 */
const AY_DAC = [
  0.0, 0.0137, 0.0205, 0.0291, 0.0423, 0.0618, 0.0847, 0.1369,
  0.1691, 0.2647, 0.3527, 0.4499, 0.5704, 0.6873, 0.8482, 1.0,
];

export class PsgAudio {
  constructor() {
    const ctx = new AudioContext();
    this.ctx = ctx;
    this.master = ctx.createGain();
    this.master.gain.value = 0.5;
    // The AY's output is unipolar and the DC is blocked by the coupling cap on
    // the way out of the machine. Model that: the AND path sits at -0.5 mean,
    // and without this the offset would eat headroom and click on every
    // amplitude change.
    const dcBlock = ctx.createBiquadFilter();
    dcBlock.type = 'highpass';
    dcBlock.frequency.value = 12;
    dcBlock.Q.value = 0.707;
    this.master.connect(dcBlock).connect(ctx.destination);

    // One LFSR step per sample, so the buffer's own noise clock is the sample
    // rate and `playbackRate` alone sets the pitch. Stored unipolar ({0,1})
    // because that is the form both the AND and the noise-only path want.
    const buffer = ctx.createBuffer(1, NOISE_PERIOD, ctx.sampleRate);
    const data = buffer.getChannelData(0);
    let lfsr = 1;
    for (let i = 0; i < data.length; i++) {
      data[i] = lfsr & 1;
      // 17-bit LFSR, feedback from bits 0 and 3 (AY-3-8910 / YM2149).
      lfsr = (lfsr >>> 1) | (((lfsr ^ (lfsr >>> 3)) & 1) << 16);
    }
    const noise = ctx.createBufferSource();
    noise.buffer = buffer;
    noise.loop = true;
    noise.start();
    this.noise = noise;
    this.noiseRate = 0;

    // The `- 1` of the AND, and the offset that recentres the noise-only path.
    const dc = ctx.createConstantSource();
    dc.offset.value = 1;
    dc.start();

    this.channels = [];
    for (let ch = 0; ch < 3; ch++) {
      // The channel's DAC: everything below sums into this one amplitude.
      const amp = ctx.createGain();
      amp.gain.value = 0;
      amp.connect(this.master);

      const osc = ctx.createOscillator();
      osc.type = 'square';
      osc.start();

      // Tone alone.
      const tone = ctx.createGain();
      tone.gain.value = 0;
      osc.connect(tone).connect(amp);

      // a*n: the oscillator scaled by the noise bit, which is 0 or 1.
      const product = ctx.createGain();
      product.gain.value = 0; // base 0, so the connection below is the whole gain
      osc.connect(product);
      noise.connect(product.gain);
      const gated = ctx.createGain();
      gated.gain.value = 0;
      product.connect(gated).connect(amp);

      // n, at 1 for the AND and 2 for noise-only.
      const noiseLevel = ctx.createGain();
      noiseLevel.gain.value = 0;
      noise.connect(noiseLevel).connect(amp);

      // -1 whenever the noise path is live.
      const offset = ctx.createGain();
      offset.gain.value = 0;
      dc.connect(offset).connect(amp);

      this.channels.push({ osc, amp, tone, gated, noiseLevel, offset, freq: 0, mode: -1 });
    }
  }

  /** @param {Uint8Array} regs R0..R10 */
  update(regs) {
    const t = this.ctx.currentTime;

    // R6 is the noise divider: f = clock / (16 * R6), with 0 behaving as 1.
    // Pitch snaps rather than glides - a drum that slides into place is wrong.
    const divider = (regs[6] & 0x1f) || 1;
    const rate = Math.min(4, Math.max(0.02, PSG_CLOCK / (16 * divider) / this.ctx.sampleRate));
    if (rate !== this.noiseRate) {
      this.noise.playbackRate.setValueAtTime(rate, t);
      this.noiseRate = rate;
    }

    for (let ch = 0; ch < 3; ch++) {
      const c = this.channels[ch];
      const period = regs[2 * ch] | ((regs[2 * ch + 1] & 0x0f) << 8);
      const vol = regs[8 + ch] & 0x0f;
      // Mixer bits are active low: 0 means the source reaches the DAC.
      const toneOn = (regs[7] & (1 << ch)) === 0 && period > 0;
      const noiseOn = (regs[7] & (8 << ch)) === 0;

      if (toneOn) {
        const freq = Math.min(12000, Math.max(20, PSG_CLOCK / (16 * period)));
        if (freq !== c.freq) {
          c.osc.frequency.setTargetAtTime(freq, t, 0.005);
          c.freq = freq;
        }
      }

      // 0 = silent, 1 = tone only, 2 = noise only, 3 = both (AND).
      const mode = (toneOn ? 1 : 0) | (noiseOn ? 2 : 0);
      if (mode !== c.mode) {
        c.mode = mode;
        // Routing snaps: these are switches, not levels.
        c.tone.gain.setValueAtTime(mode === 1 ? 1 : 0, t);
        c.gated.gain.setValueAtTime(mode === 3 ? 1 : 0, t);
        c.noiseLevel.gain.setValueAtTime(mode === 2 ? 2 : mode === 3 ? 1 : 0, t);
        c.offset.gain.setValueAtTime(mode & 2 ? -1 : 0, t);
      }

      c.amp.gain.setTargetAtTime(mode === 0 ? 0 : AY_DAC[vol] * CHANNEL_GAIN, t, 0.01);
    }
  }
}
