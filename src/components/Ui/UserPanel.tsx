import { User } from '@typings';
import { getNameInitials } from '@utils/helpers';

import { Popover } from '@components/Shared';

import { LogoutButton } from './LogoutButton';

type Props = {
  user?: User;
};

export const UserPanel: React.FC<Props> = ({ user }) => {
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
        <LogoutButton />
      </div>
    </Popover>
  );
};
