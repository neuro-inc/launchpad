import { AnchorHTMLAttributes, MouseEventHandler } from 'react';
import RouterLink from 'next/link';
import { IconProp } from '@fortawesome/fontawesome-svg-core';

import { VariantProps } from '@typings';
import { cn } from '@utils';
import { checkIsComponentWithIconChild } from '@utils/helpers';
import { buttonVariants } from '@utils/variants';

import { Icon } from '@components';

type BaseLinkProps = {
  href: string;
  theme?: boolean;
  disabled?: boolean;
  className?: string;
  icon?: IconProp;
  children?: React.ReactNode;
  onClick?: MouseEventHandler<HTMLAnchorElement>;
};

type RouterLinkProps = {
  external?: false;
  state?: any;
};

type AnchorLinkProps = {
  external: true;
  blank?: boolean;
};

type Props = AnchorHTMLAttributes<HTMLAnchorElement> &
  VariantProps<typeof buttonVariants> &
  BaseLinkProps &
  (RouterLinkProps | AnchorLinkProps);

export const Link = ({
  children,
  theme = true,
  disabled = false,
  className,
  variant,
  external = false,
  icon,
  ...props
}: Props) => {
  const isWithIcon = !!icon || checkIsComponentWithIconChild(children);
  const classNames = theme
    ? cn(buttonVariants({ variant, withIcon: isWithIcon, className }), {
        'pointer-events-none': disabled,
      })
    : className;

  if (external) {
    const { blank, ...anchorProps } =
      props as AnchorHTMLAttributes<HTMLAnchorElement> &
        Pick<AnchorLinkProps, 'blank'>;
    const target = blank ? '_blank' : '';
    const linkOptions = {
      ...anchorProps,
      className: classNames,
      target,
      disabled,
    } as AnchorHTMLAttributes<HTMLAnchorElement>;

    return (
      // eslint-disable-next-line react/no-invalid-html-attribute
      <a {...linkOptions} rel="noreferrer noopener">
        {children}
      </a>
    );
  }

  const options = {
    ...props,
    className: classNames,
    disabled,
  };

  return (
    <RouterLink {...options}>
      <Icon icon={icon} className="text-20" />
      {children}
    </RouterLink>
  );
};
