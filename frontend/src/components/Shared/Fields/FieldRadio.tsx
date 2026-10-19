import React, { InputHTMLAttributes, useId } from 'react';

import { FieldProps } from '@typings';
import { cn, getSlots } from '@utils';

import { Render } from '../Render';
import { Slot } from '../Slot';

import { FieldContainer } from './FieldContainer';
import { FieldError } from './FieldError';
import { FieldNote } from './FieldNote';

type Props = Omit<InputHTMLAttributes<HTMLInputElement>, 'size'> &
  FieldProps & {
    labelClassName?: string;
  };

export const FieldRadio = React.forwardRef<HTMLInputElement, Props>(
  (
    {
      disabled,
      required,
      className,
      containerClassName,
      labelClassName,
      label,
      error,
      note,
      children,
      ...props
    },
    ref,
  ) => {
    const id = useId();
    const { content, ...slots } = getSlots<'note' | 'error'>(children);

    return (
      <FieldContainer
        className={cn('launchpad-field--radio', containerClassName)}
        data-field={props.name}
        data-invalid={Boolean(error) || undefined}
      >
        <label
          htmlFor={id}
          className={cn(
            'launchpad-radio group flex cursor-pointer items-center gap-2',
            { 'pointer-events-none': disabled },
            className,
          )}
          data-disabled={disabled || undefined}
        >
          <input
            {...props}
            ref={ref}
            id={id}
            type="radio"
            className="launchpad-radio__input peer hidden"
            data-invalid={Boolean(error) || undefined}
            disabled={disabled}
          />
          <div className="launchpad-radio__indicator size-5 rounded-full border-2 border-neural-03 bg-background transition-colors group-hover:border-primary-light peer-checked:border-[6px] peer-checked:border-primary peer-checked:bg-neural-01 peer-disabled:border-neural-03" />
          <span className="launchpad-radio__label peer-disabled:text-neural-03">
            {content}
          </span>
        </label>

        <Render if={!!error}>
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

FieldRadio.displayName = 'Field.Radio';
