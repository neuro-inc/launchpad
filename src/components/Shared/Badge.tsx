import { VariantProps } from '@typings';
import { tv } from '@utils';

const variants = tv({
  base: 'rounded-full px-3 py-1 text-footnote-large inline-flex items-center shrink-0',
  variants: {
    variant: {
      grey: 'bg-neural-01 text-black',
      green: 'text-success-dark bg-success-subtle',
      yellow: 'text-warning-dark bg-warning-subtle',
      red: 'text-error-dark bg-error-subtle',
      primary: 'bg-primary-subtle text-primary-dark',
    },
  },
  defaultVariants: {
    variant: 'grey',
  },
});

type Props = VariantProps<typeof variants> & {
  className?: string;
  children?: React.ReactNode;
};

export const Badge = ({ className, variant, children }: Props) => {
  return <div className={variants({ variant, className })}>{children}</div>;
};
