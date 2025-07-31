import React, { InputHTMLAttributes, useId } from 'react';

import { FieldProps } from '@typings';
import { getSlots } from '@utils';
import { fieldVariants } from '@utils/variants';

import { Field, Render, Slot } from '@components';

type Props = Omit<InputHTMLAttributes<HTMLInputElement>, 'size'> &
  FieldProps & {
    labelClassName?: string;
  };

export const FieldInput = React.forwardRef<HTMLInputElement, Props>(
  (
    {
      disabled,
      required,
      autoComplete = 'off',
      className,
      containerClassName,
      labelClassName,
      variant = 'floating',
      label,
      /**
       * `" "` placeholder is required for floating label
       */
      placeholder = ' ',
      showError = true,
      error,
      note,
      children,
      ...props
    },
    ref,
  ) => {
    const id = useId();

    const slots = getSlots<'note' | 'error' | 'icon'>(children);

    const handleWheel = (event: React.WheelEvent<HTMLInputElement>) => {
      if (props.type === 'number') {
        event.currentTarget.blur();
      }
    };

    return (
      <Field.Container className={containerClassName}>
        <input
          {...props}
          ref={ref}
          id={id}
          className={fieldVariants({
            variant,
            error: !!error,
            label: !!label,
            className,
          })}
          autoComplete={autoComplete}
          disabled={disabled}
          placeholder={placeholder}
          onWheel={handleWheel}
        />
        <Field.Label
          variant={variant}
          for={id}
          required={required}
          className={labelClassName}
        >
          {label}
        </Field.Label>
        <Render if={showError}>
          <Slot slot={slots.error}>
            <Field.Error>{error}</Field.Error>
          </Slot>
        </Render>
        <Render if={!error}>
          <Slot slot={slots.note}>
            <Field.Note>{note}</Field.Note>
          </Slot>
        </Render>
        <Slot slot={slots.icon} />
      </Field.Container>
    );
  },
);

FieldInput.displayName = 'Field.Input';
