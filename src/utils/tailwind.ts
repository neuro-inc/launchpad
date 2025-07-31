import { extendTailwindMerge } from 'tailwind-merge';
import { TV, tv as tailwindVariants } from 'tailwind-variants';
import clsx, { ClassValue } from 'clsx';

const twMergeConfig = {};

const twMerge = extendTailwindMerge(twMergeConfig);

export const cn = (...classNames: ClassValue[]) => twMerge(clsx(classNames));

/**
 * todo: resolve new tailwind-variants version ReturnType error
 */
// @ts-ignore
export const tv: TV = (options) => tailwindVariants(options, { twMergeConfig });
