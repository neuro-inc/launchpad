import { VariantProps } from '@typings';
import { cn, tv } from '@utils';

const variants = tv({
  variants: {
    variant: {
      static: 'mb-2 block',
      floating:
        'absolute start-4 top-4 z-20 origin-[0] -translate-y-4 scale-75 leading-normal text-neural-04 transition-all peer-placeholder-shown:translate-y-0 peer-placeholder-shown:scale-100 peer-focus:-translate-y-4 peer-focus:scale-75 peer-focus:text-primary peer-disabled:text-neural-03',
    },
    disabled: {
      true: 'text-neural-03',
    },
  },
  defaultVariants: {
    variant: 'static',
  },
});

type Props = VariantProps<typeof variants> & {
  required?: boolean;
  disabled?: boolean;
  for?: string;
  className?: string;
  children: React.ReactNode;
};

export const FieldLabel = ({
  required = false,
  disabled = false,
  variant,
  for: htmlFor,
  className,
  children,
}: Props) => {
  if (!children) {
    return null;
  }

  return (
    <label
      className={cn(variants({ variant, disabled }), className, {
        'required-label': required,
      })}
      htmlFor={htmlFor}
    >
      {children}
    </label>
  );
};

FieldLabel.displayName = 'Field.Label';
