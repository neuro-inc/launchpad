'use client';

import { useState } from 'react';
import { usePathname } from 'next/navigation';
import { signIn } from 'next-auth/react';

import { Button } from '@components';

export const LoginButton: React.FC = () => {
  const pathname = usePathname();

  const [isLoading, setIsLoading] = useState(false);

  const handleSignIn = async () => {
    try {
      setIsLoading(true);

      const result = await signIn('keycloak', {
        redirect: false,
        callbackUrl: pathname || '/',
      });

      if (result?.url) {
        window.location.href = result.url;
      }
    } catch (err) {
      /**
       * Continue regardless of error
       */
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="flex flex-col items-center gap-2">
      <Button
        className="px-16 capitalize"
        onClick={handleSignIn}
        loading={isLoading}
      >
        Log in
      </Button>
    </div>
  );
};
