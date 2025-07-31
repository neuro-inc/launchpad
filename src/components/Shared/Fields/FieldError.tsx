import { VariantProps } from '@typings';
import { isNumber, isString, tv } from '@utils';

const variants = tv({
  base: 'w-full text-error text-caption pl-2',
  variants: {
    variant: {
      absolute: 'absolute inset-x-0 bottom-0 truncate',
      static: 'static mt-1',
    },
  },
  defaultVariants: {
    variant: 'static',
  },
});

type Props = VariantProps<typeof variants> & {
  className?: string;
  children?: React.ReactNode;
};

export const FieldError = ({ className, variant, children }: Props) => {
  const title =
    isString(children) || isNumber(children) ? (children as string) : undefined;

  return (
    <p className={variants({ variant, className })} title={title}>
      {children}
    </p>
  );
};

FieldError.displayName = 'Field.Error';
