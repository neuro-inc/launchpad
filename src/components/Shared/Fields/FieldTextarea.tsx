import React, { TextareaHTMLAttributes, useId } from 'react';
import { faCircleInfo } from '@fortawesome/pro-regular-svg-icons';
import clsx from 'clsx';

import { FieldProps } from '@typings';
import { cn, getSlots } from '@utils';
import { fieldVariants } from '@utils/variants';

import { Field, Icon, Render, Slot, Tooltip } from '@components';

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
      <Field.Container className={containerClassName}>
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
        <Field.Label
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

FieldTextarea.displayName = 'Field.Textarea';
