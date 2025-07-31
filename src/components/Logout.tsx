'use client';

import { signOut } from 'next-auth/react';

import { Button } from '@components';

export default function Logout() {
  return <Button onClick={signOut}>Signout of Keycloak</Button>;
}
