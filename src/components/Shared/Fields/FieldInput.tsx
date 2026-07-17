import React, { InputHTMLAttributes, useId } from 'react';
import { faCircleInfo } from '@fortawesome/pro-regular-svg-icons';
import clsx from 'clsx';

import { FieldProps } from '@typings';
import { getSlots } from '@utils';
import { fieldVariants } from '@utils/variants';

import { Icon } from '../Icon';
import { Render } from '../Render';
import { Slot } from '../Slot';
import { Tooltip } from '../Tooltip';

import { FieldContainer } from './FieldContainer';
import { FieldError } from './FieldError';
import { FieldLabel } from './FieldLabel';
import { FieldNote } from './FieldNote';

type Props = Omit<InputHTMLAttributes<HTMLInputElement>, 'size'> &
  FieldProps & {
    labelClassName?: string;
    tooltip?: string;
  };

export const FieldInput = React.forwardRef<HTMLInputElement, Props>(
  (
    {
      disabled,
      required,
      name,
      autoComplete = 'off',
      className,
      containerClassName,
      labelClassName,
      variant = 'floating',
      label,
      tooltip,
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
      <FieldContainer
        className={clsx('launchpad-field--input', containerClassName)}
        data-field={name}
        data-invalid={Boolean(error) || undefined}
      >
        <input
          {...props}
          ref={ref}
          id={id}
          name={name}
          className={fieldVariants({
            variant,
            error: !!error,
            label: !!label,
            className: clsx(
              'launchpad-field__control launchpad-input',
              className,
            ),
          })}
          data-invalid={Boolean(error) || undefined}
          data-variant={variant}
          autoComplete={autoComplete}
          disabled={disabled}
          placeholder={placeholder}
          onWheel={handleWheel}
        />
        <FieldLabel
          variant={variant}
          for={id}
          required={required}
          className={labelClassName}
        >
          <span
            className={clsx('launchpad-field__label-content', {
              'flex items-center gap-2': !!tooltip,
            })}
          >
            {label}
            {tooltip && (
              <Tooltip side="top">
                <Icon
                  slot="trigger"
                  icon={faCircleInfo}
                  className="text-neural-04 hover:text-neural-06"
                />
                <span className="launchpad-field__tooltip text-caption">
                  {tooltip}
                </span>
              </Tooltip>
            )}
          </span>
        </FieldLabel>
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
        <Slot slot={slots.icon} />
      </FieldContainer>
    );
  },
);

FieldInput.displayName = 'Field.Input';
