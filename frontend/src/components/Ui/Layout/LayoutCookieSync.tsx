'use client';

import { useEffect } from 'react';
import { signOut } from 'next-auth/react';

import {
  clearLaunchpadCookie,
  setLaunchpadCookie,
} from '@services/auth.services';

type Props = {
  token?: string | null;
  sessionError?: string | null;
  apiUrl: string;
};

const logCookieSyncError = (event: string, error: unknown, apiUrl: string) => {
  console.error(
    JSON.stringify({
      scope: 'launchpad-net',
      event,
      ts: new Date().toISOString(),
      apiUrl,
      error: error instanceof Error ? error.message : String(error),
    }),
  );
};

export const LayoutCookieSync: React.FC<Props> = ({
  token,
  sessionError,
  apiUrl,
}) => {
  useEffect(() => {
    if (sessionError === 'RefreshAccessTokenError') {
      clearLaunchpadCookie();
      fetch(`${apiUrl}/auth/logout`, {
        method: 'POST',
        credentials: 'include',
      }).catch((error) => {
        logCookieSyncError('cookie-sync-logout-error', error, apiUrl);
      });

      signOut({ callbackUrl: '/auth' }).catch((error) => {
        logCookieSyncError(
          'nextauth-stale-session-signout-error',
          error,
          apiUrl,
        );
      });
      return;
    }

    if (!token) {
      clearLaunchpadCookie();
      fetch(`${apiUrl}/auth/logout`, {
        method: 'POST',
        credentials: 'include',
      })
        .then((response) => {
          if (!response.ok) {
            throw new Error(`Request failed with status ${response.status}`);
          }
        })
        .catch((error) => {
          logCookieSyncError('cookie-sync-logout-error', error, apiUrl);
        });
      return;
    }

    // Legacy cookie for old API deployments that read "launchpad-token" directly.
    setLaunchpadCookie(token);

    // New API deployments: POST the token so the API sets an HttpOnly per-instance cookie.
    fetch(`${apiUrl}/auth/callback`, {
      method: 'POST',
      credentials: 'include',
      headers: {
        Authorization: `Bearer ${token}`,
        Origin: window.location.origin,
      },
    })
      .then((response) => {
        if (!response.ok) {
          throw new Error(`Request failed with status ${response.status}`);
        }
      })
      .catch((error) => {
        logCookieSyncError('cookie-sync-callback-error', error, apiUrl);
      });
  }, [token, sessionError, apiUrl]);

  return null;
};
