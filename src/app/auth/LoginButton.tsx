'use client';

import { signIn } from 'next-auth/react';

import { Button } from '@components';

export const LoginButton: React.FC = () => {
  return (
    <Button className="px-16 capitalize" onClick={() => signIn('keycloak')}>
      Log in
    </Button>
  );
};
