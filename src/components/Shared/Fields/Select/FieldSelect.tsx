import React, { SelectHTMLAttributes, useId } from 'react';
import { faCaretDown } from '@fortawesome/pro-solid-svg-icons';
import clsx from 'clsx';

import { FieldProps } from '@typings';
import { getSlots } from '@utils';
import { fieldVariants } from '@utils/variants';

import { Icon } from '../../Icon';
import { Render } from '../../Render';
import { Slot } from '../../Slot';
import { FieldContainer } from '../FieldContainer';
import { FieldError } from '../FieldError';
import { FieldLabel } from '../FieldLabel';
import { FieldNote } from '../FieldNote';

type Props = Omit<SelectHTMLAttributes<HTMLSelectElement>, 'size'> &
  FieldProps & {
    placeholder?: string;
    options?: Array<{
      value: string | number;
      text: string | number;
    }>;
  };

export const FieldSelect = React.forwardRef<HTMLSelectElement, Props>(
  (
    {
      disabled,
      required,
      name,
      className,
      containerClassName,
      variant = 'floating',
      label,
      placeholder,
      showError = true,
      error,
      options,
      note,
      children,
      ...props
    },
    ref,
  ) => {
    const id = useId();

    const slots = getSlots<'note' | 'error'>(children);

    const getSelectItems = () => {
      if (options) {
        return options.map(({ value, text }) => (
          <option key={value} value={value}>
            {text}
          </option>
        ));
      }

      return slots.content;
    };

    return (
      <FieldContainer className={containerClassName}>
        <select
          {...props}
          className={fieldVariants({
            variant,
            error: !!error,
            label: !!label,
            className,
          })}
          ref={ref}
          name={name}
          required={required}
          id={id}
          disabled={disabled}
        >
          {getSelectItems()}
        </select>
        <FieldLabel
          variant={variant}
          for={id}
          required={required}
          disabled={disabled}
        >
          {label}
        </FieldLabel>
        <Icon
          icon={faCaretDown}
          className={clsx(
            'pointer-events-none absolute right-4 top-4 text-[16px] text-neural-04',
            { 'text-neural-02': disabled },
          )}
        />
        <Render if={showError}>
          <Slot slot={slots.error}>
            <FieldError>{error}</FieldError>
          </Slot>
        </Render>
        <Render if={!error}>
          <Slot slot={slots.note}>
            <FieldNote>{note}</FieldNote>
          </Slot>
        </Render>
      </FieldContainer>
    );
  },
);

FieldSelect.displayName = 'Field.Select';
