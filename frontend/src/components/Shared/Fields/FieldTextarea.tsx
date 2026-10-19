import React, { TextareaHTMLAttributes, useId } from 'react';
import { faCircleInfo } from '@fortawesome/pro-regular-svg-icons';
import clsx from 'clsx';

import { FieldProps } from '@typings';
import { cn, getSlots } from '@utils';
import { fieldVariants } from '@utils/variants';

import { Icon } from '../Icon';
import { Render } from '../Render';
import { Slot } from '../Slot';
import { Tooltip } from '../Tooltip';

import { FieldContainer } from './FieldContainer';
import { FieldError } from './FieldError';
import { FieldLabel } from './FieldLabel';
import { FieldNote } from './FieldNote';

type Props = Omit<TextareaHTMLAttributes<HTMLTextAreaElement>, 'size'> &
  FieldProps & {
    resizable?: boolean;
    labelClassName?: string;
    tooltip?: string;
  };

export const FieldTextarea = React.forwardRef<HTMLTextAreaElement, Props>(
  (
    {
      disabled,
      required,
      name,
      autoComplete = 'off',
      className,
      resizable,
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

    return (
      <FieldContainer
        className={clsx('launchpad-field--textarea', containerClassName)}
        data-field={name}
        data-invalid={Boolean(error) || undefined}
      >
        <textarea
          {...props}
          ref={ref}
          id={id}
          name={name}
          className={cn(
            fieldVariants({
              variant,
              error: !!error,
              label: !!label,
            }),
            'launchpad-field__control launchpad-textarea min-h-[64px] resize-none pt-4',
            { 'resize-y': resizable },
            className,
          )}
          data-invalid={Boolean(error) || undefined}
          data-variant={variant}
          autoComplete={autoComplete}
          disabled={disabled}
          placeholder={placeholder}
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

FieldTextarea.displayName = 'Field.Textarea';
