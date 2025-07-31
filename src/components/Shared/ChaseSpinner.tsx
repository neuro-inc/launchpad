import { VariantProps } from '@typings';
import { cn, tv } from '@utils';

const variants = tv({
  base: 'absolute left-0 top-0 h-full w-full before:block before:h-1/4 before:w-1/4 before:rounded-full before:bg-white',
  variants: {
    color: {
      black: 'before:bg-black',
      white: 'before:bg-white',
      primary: 'before:bg-primary',
      secondary: 'before:bg-secondary',
      error: 'before:bg-error',
    },
  },
  defaultVariants: {
    color: 'white',
  },
});

type Props = VariantProps<typeof variants> & {
  className?: string;
};

export const ChaseSpinner = ({ className, color }: Props) => {
  const chaseDotClassName = cn(variants({ color }));

  return (
    <div className={cn(`chase-spinner relative size-6`, className)}>
      <div className={chaseDotClassName} />
      <div className={chaseDotClassName} />
      <div className={chaseDotClassName} />
      <div className={chaseDotClassName} />
      <div className={chaseDotClassName} />
      <div className={chaseDotClassName} />
    </div>
  );
};
