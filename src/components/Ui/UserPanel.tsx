import Link from 'next/link';

import { User } from '@typings';
import { PATH } from '@constants';
import { getNameInitials } from '@utils/helpers';

import { Popover } from '@components/Shared';

import { LogoutButton } from './LogoutButton';

type Props = {
  user?: User;
  isAdmin?: boolean;
};

export const UserPanel: React.FC<Props> = ({ user, isAdmin = false }) => {
  if (!user) {
    return null;
  }

  const { name, email } = user;

  const nameInitials = getNameInitials(name || email);

  return (
    <Popover
      showArrow={false}
      align="end"
      side="bottom"
      className="launchpad-user-panel__popover p-5"
      triggerClassName="launchpad-user-panel launchpad-user-panel__trigger"
    >
      <span
        slot="trigger"
        className="launchpad-user-panel__avatar flex size-10 items-center justify-center rounded-full bg-rebecca capitalize"
      >
        <span className="launchpad-user-panel__initials text-h7 text-white">
          {nameInitials}
        </span>
      </span>

      <div className="launchpad-user-panel__content min-w-64">
        <p className="launchpad-user-panel__email">{email}</p>
        <p className="launchpad-user-panel__name mt-0.5 text-body-small text-neural-04">
          {name}
        </p>
        {isAdmin && (
          <Link
            href={PATH.ADMIN}
            className="launchpad-user-panel__admin-link mt-4 block rounded-lg bg-primary px-4 py-2 text-center text-white transition-colors hover:bg-primary-dark"
            data-action="open-admin"
          >
            Admin Panel
          </Link>
        )}
        <LogoutButton />
      </div>
    </Popover>
  );
};
