'use client';

import { signOut } from 'next-auth/react';

import { Button } from '@components';

export default function Logout() {
  const handleLogout = async () => {
    await signOut({ redirect: false });

    window.location.href = '/api/auth/logout';
  };

  return <Button onClick={handleLogout}>Signout of Keycloak</Button>;
}
