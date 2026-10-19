'use client';

import { useEffect, useState } from 'react';
import { usePathname } from 'next/navigation';
import { signIn } from 'next-auth/react';

import { IS_LOCAL } from '@constants/app.constants';
import { deriveServerApiUrl } from '@utils/helpers/serverApiUrl';

import { Button } from '@components';

const getApiUrl = () => {
  try {
    const siteUrl =
      IS_LOCAL && process.env.NEXT_PUBLIC_SITE_URL
        ? process.env.NEXT_PUBLIC_SITE_URL
        : location.origin;

    return deriveServerApiUrl(siteUrl);
  } catch {
    return null;
  }
};

export const LoginButton: React.FC = () => {
  const pathname = usePathname();
  const [isLoading, setIsLoading] = useState(false);
  const [showProcore, setShowProcore] = useState(false);
  const [apiUrl, setApiUrl] = useState<string | null>(null);

  useEffect(() => {
    const nextApiUrl = getApiUrl();
    setApiUrl(nextApiUrl);
    if (!nextApiUrl) return;

    fetch(`${nextApiUrl}/config`, { cache: 'no-store' })
      .then((r) => r.json())
      .then((data) => {
        if (data?.keycloak?.idp_hint) {
          setShowProcore(true);
        }
      })
      .catch(() => undefined);
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
    if (!apiUrl) {
      return;
    }

    try {
      setIsLoading(true);

      const callbackUrl = getCallbackUrl();

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
    if (!apiUrl) {
      return;
    }

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
    <div className="launchpad-auth-page__actions flex flex-col items-center gap-2">
      <Button
        className="launchpad-auth-page__login-button px-16 capitalize"
        data-action="login"
        onClick={handleSignIn}
        loading={isLoading}
        disabled={!apiUrl}
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
