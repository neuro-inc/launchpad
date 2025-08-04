'use client';

import ImageComponent, { ImageProps } from 'next/image';
import { SetOptional } from 'type-fest';
import clsx from 'clsx';

type Props = SetOptional<ImageProps, 'alt'> & {
  transition?: boolean;
};

export const Image: React.FC<Props> = ({
  className,
  alt = '',
  transition = false,
  ...props
}) => {
  const handleLoad = (event: React.SyntheticEvent<HTMLImageElement>) => {
    const image = event.currentTarget;
    image.classList.remove('opacity-0');
    image.classList.add('opacity-100');
  };

  return (
    <ImageComponent
      {...props}
      alt={alt}
      className={clsx(
        { 'opacity-0 transition-opacity duration-1000': transition },
        className,
      )}
      onLoad={handleLoad}
    />
  );
};
