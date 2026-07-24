import { IconProp } from '@fortawesome/fontawesome-svg-core';
import { faArrowUpRightFromSquare } from '@fortawesome/pro-solid-svg-icons';

import { cn } from '@utils';

import { Icon, Link, Render } from '@components';

type Props = {
  external?: boolean;
  title?: string;
  to: string;
  icon?: IconProp;
  className?: string;
};

export const AppItemLink: React.FC<Props> = ({
  external,
  to,
  icon,
  className,
  title = to,
}) => {
  return (
    <Link
      external
      blank
      theme={false}
      href={to}
      className={cn(
        'launchpad-app-link flex items-center text-body-medium text-primary transition-colors hover:text-primary-dark',
        className,
      )}
    >
      <Icon
        icon={icon}
        className="launchpad-app-link__icon mr-2.5 text-[20px] text-rebecca"
      />
      <span className="launchpad-app-link__label">{title}</span>
      <Render if={external}>
        <Icon
          icon={faArrowUpRightFromSquare}
          className="launchpad-app-link__external-icon ml-1 size-5 text-[14px]"
        />
      </Render>
    </Link>
  );
};
