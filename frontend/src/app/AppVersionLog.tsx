'use client';

import { APP_COMMIT_SHA, APP_DEPLOYED_AT, APP_VERSION } from '@constants';

if (typeof window !== 'undefined') {
  // eslint-disable-next-line no-console
  console.info(
    'v%s (%s) - %s',
    APP_VERSION,
    APP_COMMIT_SHA,
    APP_DEPLOYED_AT.slice(0, 10),
  );
}

export const AppVersionLog = () => null;
