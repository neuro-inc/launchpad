import { forwardRef } from 'react';
import * as Select from '@radix-ui/react-select';

import { VariantProps } from '@typings';
import { cn, tv } from '@utils';

const variants = tv({
  variants: {
    variant: {
      base: 'rounded-lg text-textmain transition-colors hover:bg-lightgrey outline-none cursor-pointer p-1.5',
      none: '',
    },
    size: {
      normal: 'text-16 leading-24',
      smaller: 'text-14 leading-20',
    },
  },
  defaultVariants: {
    variant: 'base',
    size: 'normal',
  },
});

type Props = VariantProps<typeof variants> & {
  className?: string;
  value: string;
  children?: React.ReactNode;
};

export const FieldSelectItem = forwardRef<HTMLDivElement, Props>(
  ({ variant, size, value, children, className }, ref) => {
    return (
      <Select.Item
        ref={ref}
        value={value}
        className={variants({
          variant,
          size,
          className: cn('launchpad-select__item', className),
        })}
        data-value={value}
      >
        <Select.ItemText className="launchpad-select__item-text">
          {children}
        </Select.ItemText>
      </Select.Item>
    );
  },
);

FieldSelectItem.displayName = 'Field.SelectItem';
