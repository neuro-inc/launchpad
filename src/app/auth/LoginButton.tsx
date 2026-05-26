'use client';

import { useEffect, useState } from 'react';
import { usePathname } from 'next/navigation';
import { signIn } from 'next-auth/react';

import { Button } from '@components';

const getApiUrl = () => {
  const hostname = location.hostname;
  const match = hostname.match(/^(.+?)\.launchpad\.(.+)$/);
  if (match) {
    return `${location.protocol}//${match[1]}-api.${match[2]}`;
  }
  return null;
};

export const LoginButton: React.FC = () => {
  const pathname = usePathname();
  const [isLoading, setIsLoading] = useState(false);
  const [showProcore, setShowProcore] = useState(false);

  useEffect(() => {
    const apiUrl = getApiUrl();
    if (!apiUrl) return;

    fetch(`${apiUrl}/config`, { cache: 'no-store' })
      .then((r) => r.json())
      .then((data) => {
        if (data?.keycloak?.idp_hint) {
          setShowProcore(true);
        }
      })
      .catch(() => {});
  }, []);

  /**
   * Get the callback URL - default to /apps if on auth page
   */
  const getCallbackUrl = () => {
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

      /**
       * Log for debugging
       */
      const callbackUrl = getCallbackUrl();

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
      // Reset loading state after a delay to allow signIn to process
      setTimeout(() => {
        setIsLoading(false);
      }, 1000);
    }
  };

  const handleProcoreSignIn = async () => {
    try {
      setIsLoading(true);

      const result = await signIn('keycloak', {
        redirect: false,
        callbackUrl: '/apps',
      });

      if (result?.url) {
        const url = new URL(result.url);
        url.searchParams.set('kc_idp_hint', 'procore');
        window.location.href = url.toString();
      }
    } catch (err) {
    } finally {
      setTimeout(() => {
        setIsLoading(false);
      }, 1000);
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
      {showProcore && (
        <>
          <Button
            className="px-16 capitalize"
            onClick={handleProcoreSignIn}
            loading={isLoading}
          >
            Sign in with Procore
          </Button>
          <p className="mx-auto max-w-md text-center text-sm text-slate-500">
            ProCore login is available only for pre-created and approved
            Keycloak users.
          </p>
        </>
      )}
    </div>
  );
};
