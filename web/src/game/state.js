/**
 * Persistent game state.
 *
 * The original keeps this in the RAM block at 0xE100 (`game_state_block`) and
 * 0xE700. Field comments carry the source address so entries stay traceable to
 * the knowledge base.
 */

/** Entity pool: 32 slots of 32 bytes at 0xE300 (`init_screen_mode`, 0x428A). */
export const ENTITY_SLOTS = 32;
export const ENTITY_STRIDE = 32;

export class GameState {
  constructor() {
    /** 0xE103..0xE105 - score, 3-byte BCD, little end first. */
    this.score = new Uint8Array(3);
    /** 0xE106..0xE108 - top score; cold_start seeds 0xE107 = 0x10 (10000). */
    this.topScore = Uint8Array.from([0x00, 0x10, 0x00]);
    /**
     * 0xE111..0xE113 - the **next extra-life threshold**, 3-byte BCD like the
     * score. `title_screen_init` seeds 0x002000 (displayed 20000) and each
     * award pushes it on by 0x6000, so it is 20000 then every 60000.
     */
    this.extendAt = Uint8Array.from([0x00, 0x20, 0x00]);
    /**
     * 0xE114 - the new-record state. Bit 6 latches "the top score has been
     * beaten this game" and the low bits free-run so bit 2 blinks the TOP row
     * (`score_display_update`, 0x4AA5).
     */
    this.recordFlags = 0;
    /** 0xE701 - current round; cold_start seeds 1. */
    this.round = 1;
    /** 0xE700 - set once gameplay is running. */
    this.inGame = 0;
    /** 0xE102 - game-flow status bits read by the main loop. */
    this.flowFlags = 0;
    /** Map-script pointer for the selected round (`stage_stream_ptr_table`). */
    this.streamPtr = 0;
    /** Frame counter, incremented once per rendered frame. */
    this.frame = 0;
    /** Structures destroyed by player shots, pending the scoring rules. */
    this.hits = 0;
    /** Times the player was struck, pending `player_hit_handler` (0x4649). */
    this.playerHits = 0;
    /** Score award index from `structure_award_index_table`, pending BCD add. */
    this.pendingAward = 0;
    /** Accumulated ALC nudge from kills (0xE131 side). */
    this.alcNudge = 0;
    /** 0xE10A lives counter; title_screen_init seeds 3 (0x41E5). */
    this.lives = 3;
    /** Frames the ROUND banner (map cmd 8) stays overlaid. */
    this.bannerTimer = 0;
    /** 0xE148 bonus counter (maxed chips add, shadows subtract 5). */
    this.bonusCounter = 0;
    /** 0xE149: rotating colour index for the type-61 walkers. */
    this.descenderColorIdx = 0;
  }

  /** `cold_start` (0x4010) RAM wipe: 0xE000-0xE7FF = 0, then the two seeds. */
  reset() {
    this.score.fill(0);
    this.topScore.set([0x00, 0x10, 0x00]);
    this.round = 1;
    this.inGame = 0;
    this.flowFlags = 0;
    this.streamPtr = 0;
    this.frame = 0;
    this.extendAt = Uint8Array.from([0x00, 0x20, 0x00]);
    this.recordFlags = 0;
  }
}
