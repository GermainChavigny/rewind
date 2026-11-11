/** Live stage geometry (recomputed on resize), shared by Stage and the cursor. */
import { computeStage, type StageGeometry } from './stage';

class Viewport {
  geometry = $state<StageGeometry>(computeStage(window.innerWidth, window.innerHeight));

  constructor() {
    window.addEventListener('resize', () => {
      this.geometry = computeStage(window.innerWidth, window.innerHeight);
    });
  }
}

export const viewport = new Viewport();
