import { extendTailwindMerge } from 'tailwind-merge';
import { TV, tv as tailwindVariants } from 'tailwind-variants';
import clsx, { ClassValue } from 'clsx';

const fontSizeList = Array.from({ length: 101 }).map((_, index) => `${index}`);

const twMergeConfig = {
  extend: {
    classGroups: {
      'font-size': [{ text: fontSizeList }],
      borderRadius: ['rounded', 'rounded-theme', 'rounded-theme-lg'],
    },
  },
};

const twMerge = extendTailwindMerge(twMergeConfig);

export const cn = (...classNames: ClassValue[]) => twMerge(clsx(classNames));

/**
 * todo: resolve new tailwind-variants version ReturnType error
 */
// @ts-ignore
export const tv: TV = (options) => tailwindVariants(options, { twMergeConfig });
