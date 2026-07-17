import { tv } from './tailwind';

export const buttonVariants = tv({
  base: 'relative inline-flex cursor-pointer items-center justify-center rounded-lg py-1 px-5 transition-colors text-button h-12 gap-2',
  variants: {
    variant: {
      rebecca:
        'bg-rebecca text-white  hover:bg-rebecca-dark active:bg-rebecca disabled:bg-neural-01 disabled:text-neural-03',
      secondary:
        'bg-neural-01 text-black hover:bg-neural-02 active:bg-neural-03 disabled:bg-neural-01 disabled:text-neural-03',
      ghost:
        'text-black hover:text-primary active:text-[#010A1B] disabled:text-neural-03',
      'ghost-primary':
        'text-primary hover:text-primary-medium active:text-primary-dark disabled:text-neural-03',
      'ghost-error':
        'text-error hover:text-error-dark active:text-error disabled:text-error-light',
      'error-outline':
        'text-error hover:text-error-dark border border-error hover:border-error-dark active:border-error active:text-error disabled:text-error-light disabled:border-error-light',
      'primary-outline':
        'text-primary hover:text-white active:text-white bg-transparent hover:bg-primary-medium active:bg-primary-dark border border-primary hover:border-primary-medium active:border-primary-dark disabled:text-neural-03 disabled:border-neural-01 disabled:bg-neural-01',
      primary:
        'bg-primary-light text-white hover:bg-primary-medium active:bg-primary disabled:bg-neural-01 disabled:text-neural-03',
      error:
        'bg-error-subtle text-error hover:text-white active:text-white hover:bg-error active:bg-error-dark disabled:bg-neural-01 disabled:text-neural-02',
    },
    withIcon: {
      true: 'pl-4',
      false: '',
    },
  },
  defaultVariants: {
    variant: 'primary',
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
      true: 'border-error hover:border-error focus:border-error',
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
