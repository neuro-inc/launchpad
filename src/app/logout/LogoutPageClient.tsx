'use client';

import { useEffect } from 'react';
import { signOut } from 'next-auth/react';

import { clearLaunchpadCookie } from '@services/auth.services';

type Props = {
  apiUrl: string;
  returnTo: string;
};

export const LogoutPageClient: React.FC<Props> = ({ apiUrl, returnTo }) => {
  useEffect(() => {
    const logout = async () => {
      await fetch(`${apiUrl}/auth/logout`, {
        method: 'POST',
        credentials: 'include',
      }).catch((error) => {
        console.error(
          JSON.stringify({
            scope: 'launchpad-net',
            event: 'external-logout-error',
            ts: new Date().toISOString(),
            apiUrl,
            error: error instanceof Error ? error.message : String(error),
          }),
        );
      });

      clearLaunchpadCookie();

      await signOut({ callbackUrl: returnTo });
    };

    logout().catch((error) => {
      console.error(
        JSON.stringify({
          scope: 'launchpad-net',
          event: 'external-signout-error',
          ts: new Date().toISOString(),
          error: error instanceof Error ? error.message : String(error),
        }),
      );
      window.location.assign(returnTo);
    });
  }, [apiUrl, returnTo]);

  return (
    <main className="flex h-screen items-center justify-center">
      <div className="text-body text-secondary">Signing out...</div>
    </main>
  );
};
