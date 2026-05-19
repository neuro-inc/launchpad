import { forwardRef, useId } from 'react';
import * as Select from '@radix-ui/react-select';
import { faChevronDown } from '@fortawesome/pro-regular-svg-icons';

import { VariantProps } from '@typings';
import { cn, getSlots } from '@utils';
import { fieldVariants } from '@utils/variants';

import { Icon } from '../../Icon';
import { Slot } from '../../Slot';
import { FieldContainer } from '../FieldContainer';
import { FieldError } from '../FieldError';
import { FieldLabel } from '../FieldLabel';
import { FieldNote } from '../FieldNote';

import { FieldSelectItem as SelectItem } from './FieldSelectItem';

type Props = Omit<VariantProps<typeof fieldVariants>, 'error'> & {
  value?: string;
  defaultValue?: string;
  required?: boolean;
  disabled?: boolean;
  label?: string;
  placeholder?: string;
  className?: string;
  containerClassName?: string;
  dropdownClassName?: string;
  iconClassName?: string;
  labelClassName?: string;
  note?: string;
  error?: string;
  options?: Array<{
    value: string;
    title: string | number;
  }>;
  children?: React.ReactNode;
  onChange?: (value: string) => void;
};

/**
 * Controlled only component
 */
export const FieldCustomSelect = forwardRef<HTMLButtonElement, Props>(
  (
    {
      required,
      label,
      value,
      disabled,
      placeholder,
      className,
      containerClassName,
      dropdownClassName,
      labelClassName,
      iconClassName,
      error,
      note,
      options,
      children,
      onChange,
      ...props
    },
    ref,
  ) => {
    const id = useId();

    const slots = getSlots<'note' | 'error' | 'value' | 'placeholder'>(
      children,
    );

    const getSelectItems = () => {
      if (options) {
        return options.map(({ value, title }) => (
          <SelectItem key={value} value={value}>
            {title}
          </SelectItem>
        ));
      }

      return slots.content;
    };

    return (
      <FieldContainer className={containerClassName}>
        <FieldLabel required={required} for={id} className={labelClassName}>
          {label}
        </FieldLabel>
        <Select.Root {...props} value={value} onValueChange={onChange}>
          <Select.Trigger
            disabled={disabled}
            className={cn(
              fieldVariants({ className, error: !!error }),
              'flex w-full items-center justify-between gap-2',
              { 'pointer-events-none opacity-50': disabled },
            )}
            ref={ref}
          >
            <Select.Value
              placeholder={
                <Slot slot={slots.placeholder}>
                  <span>{placeholder}</span>
                </Slot>
              }
            >
              <Slot slot={slots.value} />
            </Select.Value>
            <Select.Icon className={cn('text-neural-03', iconClassName)}>
              <Icon className="inline-flex" icon={faChevronDown} />
            </Select.Icon>
          </Select.Trigger>
          <Select.Portal>
            <Select.Content
              position="popper"
              sideOffset={8}
              className={cn(
                'z-30 rounded-xl bg-white p-1.5 shadow-[0px_8px_24px_-4px_rgba(24,39,75,0.08),0px_6px_12px_-6px_rgba(24,39,75,0.12)] data-[state=closed]:duration-300 data-[state=open]:duration-300 data-[state=open]:animate-in data-[state=closed]:animate-out data-[state=closed]:fade-out data-[state=open]:fade-in data-[state=closed]:slide-out-to-bottom-1 data-[state=open]:slide-in-from-bottom-1',
                dropdownClassName,
              )}
            >
              <Select.Viewport>{getSelectItems()}</Select.Viewport>
            </Select.Content>
          </Select.Portal>
        </Select.Root>
        <Slot slot={slots.error}>
          <FieldError>{error}</FieldError>
        </Slot>
        <Slot slot={slots.note}>
          <FieldNote>{note}</FieldNote>
        </Slot>
      </FieldContainer>
    );
  },
);

FieldCustomSelect.displayName = 'Field.CustomSelect';
