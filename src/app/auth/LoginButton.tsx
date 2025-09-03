'use client';

import { useState } from 'react';
import { usePathname, useSearchParams } from 'next/navigation';
import { signIn } from 'next-auth/react';

import { Button } from '@components';

export const LoginButton: React.FC = () => {
  const pathname = usePathname();
  const searchParams = useSearchParams();
  const [isLoading, setIsLoading] = useState(false);

  /**
   * Get the callback URL from search params or default to /apps
   */
  const getCallbackUrl = () => {
    const callbackUrl = searchParams.get('callbackUrl');

    /**
     * If we have a callbackUrl in search params, use it
     */
    if (callbackUrl) {
      return callbackUrl;
    }

    /**
     * If we're on auth page, default to /apps
     */
    if (pathname === '/auth') {
      return '/apps';
    }

    /**
     * Otherwise use current pathname
     */
    return pathname || '/apps';
  };

  const handleSignIn = async () => {
    try {
      setIsLoading(true);

      const callbackUrl = getCallbackUrl();

      /**
       * Log for debugging
       */
      // eslint-disable-next-line no-console
      console.log('SignIn with callbackUrl:', callbackUrl);

      const result = await signIn('keycloak', {
        redirect: false,
        callbackUrl,
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
