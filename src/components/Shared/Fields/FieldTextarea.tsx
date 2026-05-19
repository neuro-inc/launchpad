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
      <FieldContainer className={containerClassName}>
        <textarea
          {...props}
          ref={ref}
          id={id}
          className={cn(
            fieldVariants({
              variant,
              error: !!error,
              label: !!label,
            }),
            'min-h-[64px] resize-none pt-4',
            { 'resize-y': resizable },
            className,
          )}
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
          <span className={clsx({ 'flex items-center gap-2': !!tooltip })}>
            {label}
            {tooltip && (
              <Tooltip side="top">
                <Icon
                  slot="trigger"
                  icon={faCircleInfo}
                  className="text-neural-04 hover:text-neural-06"
                />
                <span className="text-caption">{tooltip}</span>
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
