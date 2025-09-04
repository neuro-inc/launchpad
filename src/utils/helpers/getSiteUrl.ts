const isLocalhostHost = (host: string): boolean => {
  return (
    host === 'localhost' ||
    host === '127.0.0.1' ||
    host === '::1' ||
    host.endsWith('.localhost')
  );
};

export const getSiteUrl = async (): Promise<string> => {
  let origin: string;

  if (typeof window !== 'undefined') {
    origin = window.location.origin;
  } else {
    try {
      // eslint-disable-next-line @typescript-eslint/no-var-requires
      const { headers } = require('next/headers');

      const hdrs = await headers();
      const host = hdrs.get('host');
      // eslint-disable-next-line no-console
      console.log('host', host);

      /**
       * If no host header, fall back to environment variable
       */
      if (!host) {
        throw new Error('No host header available');
      }

      const protocol = hdrs.get('x-forwarded-proto') || 'https';

      origin = `${protocol}://${host}`;
      // eslint-disable-next-line no-console
      console.log('origin', origin);
    } catch (error) {
      // eslint-disable-next-line no-console
      console.log('getSiteUrl error:', error);

      /**
       * Try to get from environment variable first
       */
      const envUrl = process.env.NEXT_PUBLIC_SITE_URL;

      if (envUrl) {
        /**
         * Add protocol if missing
         */
        origin = envUrl.startsWith('http') ? envUrl : `https://${envUrl}`;
        // eslint-disable-next-line no-console
        console.log('Using env URL:', origin);
      } else {
        // eslint-disable-next-line no-console
        origin = 'http://foo:3000';
        // eslint-disable-next-line no-console
        console.log('Set localhost fallback', origin);
      }
    }
  }

  return origin;
};

export const getServerApiUrl = async (): Promise<string> => {
  const siteUrl = await getSiteUrl();

  let url = new URL(siteUrl);

  if (isLocalhostHost(url.hostname)) {
    const localhostServerApiUrl = process.env.NEXT_PUBLIC_SITE_URL || '';

    url = new URL(localhostServerApiUrl);

    if (!localhostServerApiUrl) {
      console.warn('NEXT_PUBLIC_SITE_URL env var is not set for local usage');
    }
  }

  const parts = url.hostname.split('.');

  parts[0] = `${parts[0]}-api`;
  url.hostname = parts.join('.');

  return url.toString().replace(/\/$/, '');
};
