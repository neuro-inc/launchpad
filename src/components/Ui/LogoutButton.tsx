'use client';

import { signOut } from 'next-auth/react';
import { faArrowRightFromBracket } from '@fortawesome/pro-regular-svg-icons';

import { Button, Icon } from '@components';

export const LogoutButton = () => {
  return (
    <Button
      variant="ghost-error"
      className="-mb-4 mt-1 pl-0 text-body"
      onClick={signOut}
    >
      <Icon icon={faArrowRightFromBracket} className="text-[20px]" />
      <span>Log out</span>
    </Button>
  );
};
