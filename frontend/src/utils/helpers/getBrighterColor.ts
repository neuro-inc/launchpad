import Color from 'color';

const isBackgroundImageValue = (value: string): boolean => {
  return (
    /^(https?:\/\/|\/|\.\/|\.\.\/|data:|blob:)/i.test(value) ||
    /^url\(/i.test(value)
  );
};

const normalizeColorValue = (value: string): string => {
  const trimmed = value.trim();

  if (/^[0-9a-f]{3,8}$/i.test(trimmed)) {
    return `#${trimmed}`;
  }

  return trimmed;
};

const parseColor = (color: string | null): ReturnType<typeof Color> | null => {
  if (!color) {
    return null;
  }

  const value = normalizeColorValue(color);

  if (!value || isBackgroundImageValue(value)) {
    return null;
  }

  try {
    return Color(value);
  } catch {
    return null;
  }
};

export const getBrighterColor = (
  color: string | null,
  whitePercentage = 88,
): string | undefined => {
  const parsedColor = parseColor(color);

  if (!parsedColor) {
    return undefined;
  }

  const clampedWhitePercentage = Math.max(0, Math.min(100, whitePercentage));
  const whiteWeight = clampedWhitePercentage / 100;

  let mixedColor = parsedColor.mix(Color('white'), whiteWeight);

  if (mixedColor.luminosity() < 0.82) {
    mixedColor = mixedColor.mix(Color('white'), 0.35);
  }

  return mixedColor.hex();
};
