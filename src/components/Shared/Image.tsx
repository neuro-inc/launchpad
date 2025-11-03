'use client';

import ImageComponent, { ImageProps } from 'next/image';
import { SetOptional } from 'type-fest';
import clsx from 'clsx';

type Props = SetOptional<ImageProps, 'alt'> & {
  transition?: boolean;
};

// List of allowed hostnames that are configured in next.config.ts
const ALLOWED_HOSTNAMES = ['storage.googleapis.com'];

const isAllowedHostname = (src: string | undefined): boolean => {
  if (!src || typeof src !== 'string') return false;

  try {
    const url = new URL(src);
    return ALLOWED_HOSTNAMES.some((hostname) => url.hostname === hostname);
  } catch {
    // If it's not a valid URL (e.g., relative path), allow Next.js to handle it
    return true;
  }
};

export const Image: React.FC<Props> = ({
  className,
  alt = '',
  transition = false,
  src,
  ...props
}) => {
  const handleLoad = (event: React.SyntheticEvent<HTMLImageElement>) => {
    const image = event.currentTarget;
    if (transition) {
      image.classList.remove('opacity-0');
      image.classList.add('opacity-100');
    }
  };

  // Check if this is an allowed hostname for optimization
  const isOptimized = src && isAllowedHostname(src as string);

  return (
    <ImageComponent
      {...props}
      src={src!}
      alt={alt}
      // Disable optimization for custom domains
      unoptimized={!isOptimized}
      className={clsx(
        {
          'opacity-0 transition-opacity duration-1000': transition,
        },
        className,
      )}
      onLoad={handleLoad}
    />
  );
};
