import React, { InputHTMLAttributes, useId } from 'react';

import { FieldProps } from '@typings';
import { cn, getSlots } from '@utils';

import { Field, Render, Slot } from '@components';

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
      <Field.Container className={containerClassName}>
        <label
          htmlFor={id}
          className={cn(
            'group flex cursor-pointer items-center gap-2',
            { 'pointer-events-none': disabled },
            className,
          )}
        >
          <input
            {...props}
            ref={ref}
            id={id}
            type="radio"
            className="peer hidden"
            disabled={disabled}
          />
          <div className="size-5 rounded-full border-2 border-neural-03 bg-background transition-colors group-hover:border-primary-light peer-checked:border-[6px] peer-checked:border-primary peer-checked:bg-neural-01 peer-disabled:border-neural-03" />
          <span className="peer-disabled:text-neural-03">{content}</span>
        </label>

        <Render if={!!error}>
          <Slot slot={slots.error}>
            <Field.Error>{error}</Field.Error>
          </Slot>
        </Render>

        <Render if={!error}>
          <Slot slot={slots.note}>
            <Field.Note>{note}</Field.Note>
          </Slot>
        </Render>
      </Field.Container>
    );
  },
);

FieldRadio.displayName = 'Field.Radio';
