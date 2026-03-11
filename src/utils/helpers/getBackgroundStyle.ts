import type { CSSProperties } from 'react';

export const getBackgroundStyle = (
  background: string | null,
): CSSProperties | undefined => {
  if (!background) {
    return undefined;
  }

  const value = background.trim();

  if (!value) {
    return undefined;
  }

  const isUrl = /^(https?:\/\/|\/|\.\/|\.\.\/|data:|blob:)/i.test(value);
  const isCssUrl = /^url\(/i.test(value);

  if (isUrl || isCssUrl) {
    return {
      backgroundImage: isCssUrl ? value : `url(${value})`,
      backgroundSize: 'cover',
      backgroundPosition: 'center',
      backgroundRepeat: 'no-repeat',
    };
  }

  return { background: value };
};
