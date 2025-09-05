const isLocalhostHost = (host: string): boolean => {
  /**
   * Extract hostname from host:port format
   */
  const hostname = host.split(':')[0];

  return (
    hostname === 'localhost' ||
    hostname === '127.0.0.1' ||
    hostname === '::1' ||
    hostname.endsWith('.localhost')
  );
};

export const getSiteUrl = async (): Promise<string> => {
  if (typeof window !== 'undefined') {
    return window.location.origin;
  }

  try {
    // eslint-disable-next-line @typescript-eslint/no-var-requires
    const { headers } = require('next/headers');

    const hdrs = await headers();
    const host = hdrs.get('host');
    // eslint-disable-next-line no-console
    console.log('host', host);

    if (!host) {
      throw new Error('No host header available');
    }

    if (isLocalhostHost(host)) {
      const envUrl = process.env.NEXT_PUBLIC_SITE_URL;
      if (envUrl) {
        // eslint-disable-next-line no-console
        console.log('Using localhost env URL:', envUrl);
        return envUrl;
      }
    }

    /**
     * Try x-origin header (set by middleware)
     */
    const xOrigin = hdrs.get('x-origin');
    if (xOrigin) {
      // eslint-disable-next-line no-console
      console.log('Using x-origin:', xOrigin);
      return xOrigin;
    }

    /**
     * Fallback to constructing from host and protocol headers
     */
    const protocol = hdrs.get('x-forwarded-proto') || 'https';
    const origin = `${protocol}://${host}`;

    // eslint-disable-next-line no-console
    console.log('Constructed origin:', origin);
    return origin;
  } catch (error) {
    // eslint-disable-next-line no-console
    console.error('getSiteUrl error (likely outside request scope):', error);

    /**
     * Fallback when headers() is called outside request scope
     * This commonly happens during auth flows
     */
    const envUrl = process.env.NEXT_PUBLIC_SITE_URL!;

    console.log('Using fallback env URL:', envUrl);

    return envUrl;
  }
};

export const getServerApiUrl = async (): Promise<string> => {
  const siteUrl = await getSiteUrl();

  const url = new URL(siteUrl);
  const parts = url.hostname.split('.');

  parts[0] = `${parts[0]}-api`;
  url.hostname = parts.join('.');

  return url.toString().replace(/\/$/, '');
};
