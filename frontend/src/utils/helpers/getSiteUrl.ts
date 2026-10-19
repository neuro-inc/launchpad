import { IS_LOCAL } from '@constants';

import { deriveServerApiUrl } from './serverApiUrl';

const getOrigin = (url: string): string => new URL(url).origin;

export const getSiteUrl = async (): Promise<string> => {
  if (typeof window !== 'undefined') {
    return window.location.origin;
  }

  try {
    // eslint-disable-next-line @typescript-eslint/no-var-requires
    const { headers } = require('next/headers');

    const hdrs = await headers();
    const host = hdrs.get('host');

    if (!host) {
      throw new Error('No host header available');
    }

    /**
     * Try x-origin header (set by middleware)
     */
    const xOrigin = hdrs.get('x-origin');
    if (xOrigin) {
      return xOrigin;
    }

    /**
     * Fallback to constructing from host and protocol headers
     */
    const protocol = hdrs.get('x-forwarded-proto') || 'https';
    const origin = `${protocol}://${host}`;

    return origin;
  } catch (error) {
    if (IS_LOCAL && process.env.NEXT_PUBLIC_SITE_URL) {
      return getOrigin(process.env.NEXT_PUBLIC_SITE_URL);
    }

    console.error(
      JSON.stringify({
        scope: 'launchpad-net',
        event: 'site-url-resolution-error',
        ts: new Date().toISOString(),
        error:
          error instanceof Error
            ? { name: error.name, message: error.message }
            : { message: String(error) },
      }),
    );

    throw error;
  }
};

export const getServerApiUrl = async (): Promise<string> => {
  const siteUrl =
    IS_LOCAL && process.env.NEXT_PUBLIC_SITE_URL
      ? process.env.NEXT_PUBLIC_SITE_URL
      : await getSiteUrl();

  return deriveServerApiUrl(siteUrl);
};
