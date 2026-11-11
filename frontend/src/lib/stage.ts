/**
 * The UI is laid out on a fixed 720×576 "stage" (PAL SD, the CRT's native
 * mode) and scaled to fit a 4:3 frame:
 *
 * - On a 720×576 output shown 4:3 by the TV (non-square pixels), the frame is
 *   the whole screen and the scale is exactly 1 — v1 sizes are kept as-is.
 * - On other screens, the frame is the largest 4:3 box (pillarbox on 16:9).
 *   Scales may differ on x and y, like a CRT's non-square pixels.
 *
 * Videos are NOT on the stage: they always use the full screen, so 16:9
 * content stays full screen.
 */

export const STAGE_W = 720;
export const STAGE_H = 576;

export interface StageGeometry {
  left: number;
  top: number;
  width: number;
  height: number;
  scaleX: number;
  scaleY: number;
}

/** Viewports this close to 4:3 or 5:4 are treated as a full-screen 4:3 TV. */
function isTvShaped(ratio: number): boolean {
  return ratio >= 1.2 && ratio <= 1.4;
}

export function computeStage(viewW: number, viewH: number): StageGeometry {
  let width = viewW;
  let height = viewH;
  if (!isTvShaped(viewW / viewH)) {
    if (viewW / viewH > 4 / 3) width = Math.round((viewH * 4) / 3);
    else height = Math.round((viewW * 3) / 4);
  }
  return {
    left: Math.round((viewW - width) / 2),
    top: Math.round((viewH - height) / 2),
    width,
    height,
    scaleX: width / STAGE_W,
    scaleY: height / STAGE_H,
  };
}
