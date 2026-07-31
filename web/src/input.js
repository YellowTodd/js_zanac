/**
 * Input state, kept in the same shape the original engine uses so the game
 * code reads the way kb/guides/keyboard-input.md describes it.
 *
 * The engine stores one active-low byte at 0xE100 (`read_player_input`,
 * 0x4343): a bit is CLEAR while its control is held.
 *
 *   bit 0 UP      bit 4 shot   (SPACE or SHIFT, or joystick trigger A)
 *   bit 1 DOWN    bit 5 fire   (SPACE or Z,     or joystick trigger B)
 *   bit 2 LEFT    bit 6 joystick port B trigger A
 *   bit 3 RIGHT   bit 7 joystick port B trigger B
 */

export const IN_UP = 0x01;
export const IN_DOWN = 0x02;
export const IN_LEFT = 0x04;
export const IN_RIGHT = 0x08;
export const IN_SHOT = 0x10;
export const IN_FIRE = 0x20;
export const IN_IDLE = 0xff;

/** Extra keys the engine reads straight off the keyboard matrix. */
export const KEY_ESC = 'Escape';
export const KEY_PAUSE = 'F1';
/**
 * Zanac reads both pause keys from MSX matrix row 7, and **SELECT modifies
 * STOP** rather than pausing on its own (0x4DB7): STOP alone gives the
 * blinking PAUSE caption, STOP+SELECT the silent hold. F2 stands in for
 * SELECT.
 */
export const KEY_SELECT = 'F2';

const BINDINGS = new Map([
  ['ArrowUp', IN_UP],
  ['KeyW', IN_UP],
  ['ArrowDown', IN_DOWN],
  ['KeyS', IN_DOWN],
  ['ArrowLeft', IN_LEFT],
  ['KeyA', IN_LEFT],
  ['ArrowRight', IN_RIGHT],
  ['KeyD', IN_RIGHT],
  ['ShiftLeft', IN_SHOT],
  ['ShiftRight', IN_SHOT],
  ['KeyZ', IN_FIRE],
  ['KeyX', IN_FIRE],
  ['Space', IN_SHOT | IN_FIRE],
]);

export class Input {
  constructor() {
    /** Active-low input byte, the 0xE100 equivalent. */
    this.state = IN_IDLE;
    /** Raw key set, for controls the engine polls with SNSMAT directly. */
    this.keys = new Set();
    /** One-frame memory behind the rising-edge fire test (`0xE147` bit 0). */
    this.firePrimed = false;
    this._held = new Set();
  }

  /** @param {EventTarget} target usually `window` */
  attach(target) {
    const onDown = (/** @type {KeyboardEvent} */ e) => {
      if (
        BINDINGS.has(e.code) ||
        e.code === KEY_ESC ||
        e.code === KEY_PAUSE ||
        e.code === KEY_SELECT
      ) {
        e.preventDefault();
      }
      this.keys.add(e.code);
      this._held.add(e.code);
      this._recompute();
    };
    const onUp = (/** @type {KeyboardEvent} */ e) => {
      this.keys.delete(e.code);
      this._held.delete(e.code);
      this._recompute();
    };
    const onBlur = () => {
      this.keys.clear();
      this._held.clear();
      this._recompute();
    };
    target.addEventListener('keydown', onDown);
    target.addEventListener('keyup', onUp);
    target.addEventListener('blur', onBlur);
    return () => {
      target.removeEventListener('keydown', onDown);
      target.removeEventListener('keyup', onUp);
      target.removeEventListener('blur', onBlur);
    };
  }

  _recompute() {
    let state = IN_IDLE;
    for (const code of this._held) {
      const mask = BINDINGS.get(code);
      if (mask !== undefined) state &= ~mask & 0xff;
    }
    this.state = state;
  }

  /** True while the control is held. */
  held(mask) {
    return (this.state & mask) === 0;
  }

  isDown(code) {
    return this.keys.has(code);
  }

  /**
   * Rising-edge fire test, the `input_edge_fire` (0x46BC) behaviour: true only
   * on the first frame a fire control goes down, so a button held over from a
   * previous screen does not skip anything.
   */
  firePressedEdge() {
    const down = (this.state & (IN_SHOT | IN_FIRE)) !== (IN_SHOT | IN_FIRE);
    const edge = down && !this.firePrimed;
    this.firePrimed = down;
    return edge;
  }
}
