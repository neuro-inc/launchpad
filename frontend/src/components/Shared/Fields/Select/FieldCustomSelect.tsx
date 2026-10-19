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
  name?: string;
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
      name,
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
      <FieldContainer
        className={cn('launchpad-field--custom-select', containerClassName)}
        data-field={name}
        data-invalid={Boolean(error) || undefined}
      >
        <FieldLabel required={required} for={id} className={labelClassName}>
          {label}
        </FieldLabel>
        <Select.Root
          {...props}
          name={name}
          value={value}
          onValueChange={onChange}
        >
          <Select.Trigger
            id={id}
            disabled={disabled}
            className={cn(
              fieldVariants({ className, error: !!error }),
              'launchpad-field__control launchpad-select launchpad-select__trigger flex w-full items-center justify-between gap-2',
              { 'pointer-events-none opacity-50': disabled },
            )}
            data-invalid={Boolean(error) || undefined}
            ref={ref}
          >
            <Select.Value
              className="launchpad-select__value"
              placeholder={
                <Slot slot={slots.placeholder}>
                  <span className="launchpad-select__placeholder">
                    {placeholder}
                  </span>
                </Slot>
              }
            >
              <Slot slot={slots.value} />
            </Select.Value>
            <Select.Icon
              className={cn(
                'launchpad-select__icon text-neural-03',
                iconClassName,
              )}
            >
              <Icon className="inline-flex" icon={faChevronDown} />
            </Select.Icon>
          </Select.Trigger>
          <Select.Portal>
            <Select.Content
              position="popper"
              sideOffset={8}
              className={cn(
                'launchpad-select__dropdown z-30 rounded-xl bg-white p-1.5 shadow-[0px_8px_24px_-4px_rgba(24,39,75,0.08),0px_6px_12px_-6px_rgba(24,39,75,0.12)] data-[state=closed]:duration-300 data-[state=open]:duration-300 data-[state=open]:animate-in data-[state=closed]:animate-out data-[state=closed]:fade-out data-[state=open]:fade-in data-[state=closed]:slide-out-to-bottom-1 data-[state=open]:slide-in-from-bottom-1',
                dropdownClassName,
              )}
            >
              <Select.Viewport className="launchpad-select__viewport">
                {getSelectItems()}
              </Select.Viewport>
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
