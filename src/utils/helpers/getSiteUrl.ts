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
      const protocol = hdrs.get('x-forwarded-proto') || 'https';

      origin = `${protocol}://${host}`;
    } catch {
      origin = 'http://localhost:3000';
    }
  }

  const current = new URL(origin);

  if (isLocalhostHost(current.hostname)) {
    origin = 'https://launchpad.apps.dev.apolo.us';
  }

  return origin;
};

export const getServerApiUrl = async (): Promise<string> => {
  const siteUrl = await getSiteUrl();
  const url = new URL(siteUrl);
  const parts = url.hostname.split('.');

  parts[0] = `${parts[0]}-api`;
  url.hostname = parts.join('.');

  return url.toString().replace(/\/$/, '');
};
