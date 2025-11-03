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
  const nameInitials = getNameInitials(name);

  return (
    <Popover showArrow={false} align="end" side="bottom" className="p-5">
      <div
        slot="trigger"
        className="flex size-10 items-center justify-center rounded-full bg-rebecca"
      >
        <span className="text-h7 text-white">{nameInitials}</span>
      </div>
      <div className="min-w-64">
        <p>{email}</p>
        <p className="mt-0.5 text-body-small text-neural-04">{name}</p>
        {isAdmin && (
          <Link
            href={PATH.ADMIN}
            className="mt-4 block rounded-lg bg-primary px-4 py-2 text-center text-white transition-colors hover:bg-primary-dark"
          >
            Admin Panel
          </Link>
        )}
        <LogoutButton />
      </div>
    </Popover>
  );
};
