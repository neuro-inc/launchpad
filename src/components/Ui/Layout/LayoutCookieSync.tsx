'use client';

import { useEffect } from 'react';

import {
  clearLaunchpadCookie,
  setLaunchpadCookie,
} from '@services/auth.services';

type Props = {
  token?: string | null;
  apiUrl: string;
};

export const LayoutCookieSync: React.FC<Props> = ({ token, apiUrl }) => {
  useEffect(() => {
    if (!token) {
      clearLaunchpadCookie();
      fetch(`${apiUrl}/auth/logout`, {
        method: 'POST',
        credentials: 'include',
      }).catch(() => {});
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
    }).catch(() => {});
  }, [token, apiUrl]);

  return null;
};
