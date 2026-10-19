import { extendTailwindMerge } from 'tailwind-merge';
import { TV, tv as tailwindVariants } from 'tailwind-variants';
import clsx, { ClassValue } from 'clsx';

const twMergeConfig = {
  classGroups: {
    'font-size': [
      'text-h0',
      'text-h1',
      'text-h2',
      'text-h3',
      'text-h4',
      'text-h5',
      'text-h6',
      'text-h7',
      'text-headline',
      'text-body',
      'text-body-medium',
      'text-body-small',
      'text-footnote',
      'text-footnote-large',
      'text-caption',
      'text-caption-2',
      'text-caption-3',
      'text-button',
    ],
  },
};

const twMerge = extendTailwindMerge(twMergeConfig);

export const cn = (...classNames: ClassValue[]) => twMerge(clsx(classNames));

export const tv: TV = (options) => tailwindVariants(options, { twMergeConfig });
