import { IconProp } from '@fortawesome/fontawesome-svg-core';
import { faArrowUpRightFromSquare } from '@fortawesome/pro-solid-svg-icons';

import { Icon, Link, Render } from '@components';

type Props = {
  external?: boolean;
  title?: string;
  to: string;
  icon?: IconProp;
};

export const AppItemLink: React.FC<Props> = ({
  external,
  to,
  icon,
  title = to,
}) => {
  return (
    <Link
      external
      blank
      theme={false}
      href={to}
      className="flex items-center text-body-medium text-primary transition-colors hover:text-primary-dark"
    >
      <Icon icon={icon} className="mr-2.5 text-[20px] text-rebecca" />
      <span>{title}</span>
      <Render if={external}>
        <Icon
          icon={faArrowUpRightFromSquare}
          className="ml-1 size-5 text-[14px]"
        />
      </Render>
    </Link>
  );
};
