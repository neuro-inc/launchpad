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
      className="launchpad-user-panel__logout -mb-4 mt-1 w-full justify-start pl-0 text-body"
      data-action="logout"
      onClick={handleLogout}
      loading={isLoggingOut}
      disabled={isLoggingOut}
    >
      <Icon
        icon={faArrowRightFromBracket}
        className="launchpad-user-panel__logout-icon text-[20px]"
      />
      <span className="launchpad-user-panel__logout-label">Log out</span>
    </Button>
  );
};
