'use client';

import { ButtonHTMLAttributes, forwardRef } from 'react';
import { IconProp } from '@fortawesome/fontawesome-svg-core';

import { VariantProps } from '@typings';
import { cn } from '@utils';
import { checkIsComponentWithIconChild } from '@utils/helpers';
import { buttonVariants } from '@utils/variants';

import { ChaseSpinner } from './ChaseSpinner';
import { Icon } from './Icon';

type Props = VariantProps<typeof buttonVariants> &
  ButtonHTMLAttributes<HTMLButtonElement> & {
    theme?: boolean;
    stopPropagation?: boolean;
    loading?: boolean;
    icon?: IconProp;
    onClick?: (event: React.MouseEvent<HTMLButtonElement>) => unknown;
  };

export const Button = forwardRef<HTMLButtonElement, Props>(
  (
    {
      children,
      theme,
      stopPropagation = true,
      loading = false,
      disabled = false,
      className,
      variant,
      type = 'button',
      icon,
      onClick,
      ...props
    },
    ref,
  ) => {
    const isLoading = !theme && loading;
    const isWithIcon = !!icon || checkIsComponentWithIconChild(children);

    const classNames = theme
      ? className
      : cn(buttonVariants({ variant, withIcon: isWithIcon, className }), {
          'pointer-events-none': loading || disabled,
        });

    const handleClick = (event: React.MouseEvent<HTMLButtonElement>) => {
      if (stopPropagation) {
        event.stopPropagation();
      }

      if (typeof onClick === 'function') {
        onClick(event);
      }
    };

    const getLoaderColor = () => {
      if (disabled) {
        return 'black';
      }

      switch (variant) {
        case 'ghost':
        case 'secondary':
          return 'black';
        case 'ghost-primary':
        case 'primary-outline':
          return 'primary';
        case 'error':
        case 'error-outline':
        case 'ghost-error':
          return 'error';
        default:
          return 'white';
      }
    };

    return (
      <button
        {...props}
        // eslint-disable-next-line react/button-has-type
        type={type}
        disabled={disabled}
        className={classNames}
        onClick={handleClick}
        ref={ref}
      >
        {isLoading && (
          <ChaseSpinner
            className="absolute right-4 transition-all"
            color={getLoaderColor()}
          />
        )}
        <Icon icon={icon} className="text-20" />
        {children}
      </button>
    );
  },
);

Button.displayName = 'Button';
