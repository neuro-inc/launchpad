'use client';

import { signOut } from 'next-auth/react';
import { faArrowRightFromBracket } from '@fortawesome/pro-regular-svg-icons';

import { request } from '@utils/helpers';

import { Button, Icon } from '@components';

export const LogoutButton = () => {
  const handleLogout = async () => {
    try {
      await request('/auth/logout', { method: 'POST' });
      await signOut({ redirect: false });

      window.location.href = '/api/auth/logout';
    } catch (error) {
      console.error('Error signing out:', error);
    }
  };

  return (
    <Button
      variant="ghost-error"
      className="-mb-4 mt-1 pl-0 text-body"
      onClick={handleLogout}
    >
      <Icon icon={faArrowRightFromBracket} className="text-[20px]" />
      <span>Log out</span>
    </Button>
  );
};
