'use client';

import { useEffect } from 'react';
import { useSession } from 'next-auth/react';

import { setLaunchpadCookie } from '@services/auth.services';

export const SetCookieClient: React.FC = () => {
  const { data: session, status } = useSession();

  useEffect(() => {
    const run = async () => {
      try {
        const token = (session as any)?.accessToken;

        // setLaunchpadCookie deduplicates by token via lastToken — no window guard needed
        if (status === 'authenticated' && token) {
          await setLaunchpadCookie(token);
        }
      } catch (e) {
        // do not block UI on failure
        console.error('setLaunchpadCookie failed', e);
      }
    };

    run();
  }, [status, session]);

  return null;
};

export default SetCookieClient;
