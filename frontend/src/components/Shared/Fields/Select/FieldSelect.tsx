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
          <option
            key={value}
            value={value}
            className="launchpad-select__option"
          >
            {text}
          </option>
        ));
      }

      return slots.content;
    };

    return (
      <FieldContainer
        className={clsx('launchpad-field--select', containerClassName)}
        data-field={name}
        data-invalid={Boolean(error) || undefined}
      >
        <select
          {...props}
          className={fieldVariants({
            variant,
            error: !!error,
            label: !!label,
            className: clsx(
              'launchpad-field__control launchpad-select',
              className,
            ),
          })}
          ref={ref}
          name={name}
          required={required}
          id={id}
          disabled={disabled}
          data-invalid={Boolean(error) || undefined}
          data-variant={variant}
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
            'launchpad-select__icon pointer-events-none absolute right-4 top-4 text-[16px] text-neural-04',
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
