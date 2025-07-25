import { tv } from './tailwind';

export const buttonVariants = tv({
  base: 'relative flex cursor-pointer items-center justify-center rounded-md py-1 transition-colors h-10 border border-transparent',
  variants: {
    variant: {
      /**
       * Solid
       */
      primary:
        'bg-primary text-white hover:bg-serenity disabled:bg-ash disabled:text-[#999999]',
      secondary:
        'bg-gradient-to-r from-[#EB001B] via-[#9F0075] to-[#EB001B] bg-[length:200%_200%] text-white hover:bg-[100%_100%] disabled:bg-ash disabled:bg-none disabled:text-[#999999] transition-all',
      'white-primary': 'bg-white text-primary hover:text-serenity',
      'white-secondary':
        'bg-white text-secondary hover:text-success disabled:bg-ash disabled:text-[#999999]',

      /**
       * Outline
       */
      'outline-primary':
        'bg-transparent border border-primary hover:border-primary-dark text-primary hover:text-primary-dark',
      'outline-secondary':
        'bg-transparent border border-secondary hover:border-secondary-light hover:bg-secondary-light text-primary hover:text-white',

      /**
       * Ghost
       */
      ghost: 'text-primary hover:text-primary-light',

      /**
       * Theme
       */
      'primary-gradient':
        'bg-secondary text-white hover:bg-secondary-dark disabled:bg-ash disabled:text-[#999999] bg-gradient-to-l from-red-500 to-purple-500 hover:bg-gradient-to-r hover:from-purple-500 hover:to-red-500',
    },
    size: {
      /**
       * There is some conflict for using
       * `size` text-{number} and `variant` text-${color}
       * with tailwind-merge and tailwind-variants
       */
      larger: 'px-8 text-[14px] font-400',
      medium: 'px-4 text-[11px]',
    },
    withIcon: {
      true: 'pl-4',
      false: '',
    },
  },
  defaultVariants: {
    variant: 'primary',
    size: 'medium',
    withIcon: false,
  },
});

export const fieldVariants = tv({
  base: 'h-12 px-2 rounded-theme bg-transparent placeholder:text-pewterglow border border-pewterglow hover:border-primary focus:border-primary disabled:pointer-events-none w-full peer appearance-none text-14 py-1 disabled:text-silvermist disabled:border-silvermist',
  variants: {
    variant: {
      static: 'transition-colors text-14',
      floating: 'block transition-all text-14',
    },
    label: {
      true: 'pt-2',
    },
    error: {
      true: '!border-error',
    },
  },
  defaultVariants: {
    variant: 'floating',
  },
});

export const chaseSpinnerVariants = tv({
  base: 'absolute left-0 top-0 h-full w-full before:block before:h-1/4 before:w-1/4 before:rounded-full before:bg-white',
  variants: {
    color: {
      white: 'before:bg-white',
      primary: 'before:bg-primary',
      secondary: 'before:bg-secondary',
    },
  },
  defaultVariants: {
    color: 'white',
  },
});

export const layoutContainerVariants = tv({
  base: 'mx-auto w-full px-6 md:px-4 sm:px-2',
  variants: {
    variant: {
      wider: 'max-w-[1820px]',
      /**
       * Includes horizontal 24px padding
       */
      shorter: 'max-w-[1548px]',
      full: 'max-w-none',
    },
  },
  defaultVariants: {
    variant: 'shorter',
  },
});
