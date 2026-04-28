'use client';

import { useEffect } from 'react';

const COOKIE_EXPIRE_HEADER = 'expires=Thu, 01 Jan 1970 00:00:00 UTC; path=/;';

const ResetLaunchpadCookieClient: React.FC = () => {
  useEffect(() => {
    document.cookie = `launchpad-token=; ${COOKIE_EXPIRE_HEADER}`;
  }, []);

  return null;
};

export default ResetLaunchpadCookieClient;
