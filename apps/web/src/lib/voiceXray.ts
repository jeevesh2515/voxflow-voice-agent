// ponytail: single source for time → layer
export function clampMs(n: number): number {
  return Math.max(0, Math.min(196, Math.round(n)));
}

export function getActiveLayerIndex(ms: number): number {
  const c = clampMs(ms);
  if (c < 56) return 0;
  if (c < 100) return 1;
  if (c < 148) return 2;
  return 3;
}

