/**
 * Channel logo ids: "retro:1" / "retro:2" are the two retro variants (the
 * background follows the channel number, the name is drawn over it),
 * "custom:<file>" an image from <data>/logos. No logo means retro variant 1.
 */
export function retroVariant(logo: string | null | undefined): 1 | 2 | null {
  if (!logo || logo === 'retro:1') return 1;
  if (logo === 'retro:2') return 2;
  return null;
}
