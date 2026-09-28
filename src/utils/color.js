export function hexToRgb(hex) {
  const cleaned = hex.replace('#', '');
  const full =
    cleaned.length === 3
      ? cleaned
          .split('')
          .map((c) => c + c)
          .join('')
      : cleaned;
  const value = parseInt(full, 16);
  if (Number.isNaN(value) || full.length !== 6) return { r: 196, g: 7, b: 61 };
  return { r: (value >> 16) & 255, g: (value >> 8) & 255, b: value & 255 };
}

const scale = ({ r, g, b }, factor) => ({
  r: Math.round(r * factor),
  g: Math.round(g * factor),
  b: Math.round(b * factor),
});

const toChannels = ({ r, g, b }) => `${r} ${g} ${b}`;

/** Writes the brand color and its darker shades as CSS variables on :root. */
export function applyBrandColor(hex) {
  const base = hexToRgb(hex);
  const root = document.documentElement.style;
  root.setProperty('--brand', toChannels(base));
  root.setProperty('--brand-deep', toChannels(scale(base, 0.72)));
  root.setProperty('--brand-night', toChannels(scale(base, 0.32)));
  document.querySelector('meta[name="theme-color"]')?.setAttribute('content', hex);
}

export function withAlpha(hex, alpha) {
  const { r, g, b } = hexToRgb(hex);
  return `rgba(${r}, ${g}, ${b}, ${alpha})`;
}

/** Picks a readable text color (dark or light) for a given background. */
export function readableTextOn(hex) {
  const { r, g, b } = hexToRgb(hex);
  const luminance = (0.299 * r + 0.587 * g + 0.114 * b) / 255;
  return luminance > 0.62 ? '#1D0F14' : '#FFFFFF';
}

export const TEAM_COLOR_PRESETS = [
  '#F5921E', // orbit orange
  '#1F6FE0', // globe blue
  '#8B3DFF', // violet
  '#12B886', // emerald
  '#E8318A', // magenta
  '#00B4D8', // cyan
  '#FFC83D', // yellow
  '#2E3A59', // slate
  '#E03131', // red
  '#7AC74F', // lime
];
