import { forwardRef } from 'react';
import { faCheck } from '@fortawesome/pro-regular-svg-icons';
import clsx from 'clsx';

import { cn, getSlots } from '@utils';

import { Field, Icon, Slot } from '@components';

type Props = React.InputHTMLAttributes<HTMLInputElement> & {
  label?: string;
  containerClassName?: string;
  error?: string | undefined;
  note?: string;
};

export const FieldCheckbox = forwardRef<HTMLInputElement, Props>(
  (
    {
      name,
      className,
      containerClassName,
      disabled,
      error,
      note,
      children,
      ...props
    },
    ref,
  ) => {
    const { content, ...slots } = getSlots<'note' | 'error'>(children);

    return (
      <Field.Container className={containerClassName}>
        <label
          htmlFor={name}
          className={cn(
            'group flex cursor-pointer items-start gap-2 text-body text-neural-04',
            className,
          )}
        >
          <input
            {...props}
            type="checkbox"
            ref={ref}
            id={name}
            className="peer absolute opacity-0"
            name={name}
            disabled={disabled}
          />
          <Icon
            className={clsx(
              'relative top-px rounded-[4px] border border-neural-02 bg-transparent pt-0.5 text-[16px] text-transparent transition-colors peer-checked:border-primary peer-checked:bg-primary peer-checked:text-white',
              { 'border-error': !!error },
            )}
            icon={faCheck}
          />
          <span>{content}</span>
        </label>
        <Slot slot={slots.error}>
          <Field.Error>{error}</Field.Error>
        </Slot>
        <Slot slot={slots.note}>
          <Field.Note>{note}</Field.Note>
        </Slot>
      </Field.Container>
    );
  },
);

FieldCheckbox.displayName = 'Field.Checkbox';
