'use client';

import { useState } from 'react';
import { signOut } from 'next-auth/react';
import { faArrowRightFromBracket } from '@fortawesome/pro-regular-svg-icons';

import { request } from '@utils/helpers';

import { Button, Icon } from '@components';

export const LogoutButton = () => {
  const [isLoggingOut, setIsLoggingOut] = useState(false);

  const handleLogout = async () => {
    if (isLoggingOut) {
      return;
    }

    setIsLoggingOut(true);

    try {
      await request('/auth/logout', { method: 'POST' });
      await signOut();
    } catch (error) {
      console.error('Error signing out:', error);
      setIsLoggingOut(false);
    }
  };

  return (
    <Button
      variant="ghost-error"
      className="-mb-4 mt-1 w-full justify-start pl-0 text-body"
      onClick={handleLogout}
      loading={isLoggingOut}
      disabled={isLoggingOut}
    >
      <Icon icon={faArrowRightFromBracket} className="text-[20px]" />
      <span>Log out</span>
    </Button>
  );
};
