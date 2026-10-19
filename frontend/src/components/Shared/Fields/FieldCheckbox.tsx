import { forwardRef } from 'react';
import { faCheck } from '@fortawesome/pro-regular-svg-icons';
import clsx from 'clsx';

import { cn, getSlots } from '@utils';

import { Icon } from '../Icon';
import { Slot } from '../Slot';

import { FieldContainer } from './FieldContainer';
import { FieldError } from './FieldError';
import { FieldNote } from './FieldNote';

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
      <FieldContainer
        className={cn('launchpad-field--checkbox', containerClassName)}
        data-field={name}
        data-invalid={Boolean(error) || undefined}
      >
        <label
          htmlFor={name}
          className={cn(
            'launchpad-checkbox group flex cursor-pointer items-start gap-2 text-body text-neural-04',
            className,
          )}
          data-disabled={disabled || undefined}
        >
          <input
            {...props}
            type="checkbox"
            ref={ref}
            id={name}
            className="launchpad-checkbox__input peer absolute opacity-0"
            data-invalid={Boolean(error) || undefined}
            name={name}
            disabled={disabled}
          />
          <Icon
            className={clsx(
              'launchpad-checkbox__indicator relative top-px rounded-[4px] border border-neural-02 bg-transparent pt-0.5 text-[16px] text-transparent transition-colors peer-checked:border-primary peer-checked:bg-primary peer-checked:text-white',
              { 'border-error': !!error },
            )}
            icon={faCheck}
          />
          <span className="launchpad-checkbox__label">{content}</span>
        </label>
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

FieldCheckbox.displayName = 'Field.Checkbox';
