'use client';

import { useEffect } from 'react';

import {
  clearLaunchpadCookie,
  setLaunchpadCookie,
} from '@services/auth.services';

type Props = {
  token?: string | null;
};

export const LayoutCookieSync: React.FC<Props> = ({ token }) => {
  useEffect(() => {
    if (!token) {
      clearLaunchpadCookie();
      return;
    }

    void setLaunchpadCookie(token).catch(() => {
      clearLaunchpadCookie();
    });
  }, [token]);

  return null;
};
