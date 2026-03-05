import { IS_LOCAL } from '@constants';

const normalizeUrl = (url: string): string => url.replace(/\/$/, '');

const PREVIEW_SITE_HOSTNAME_PATTERN = /^([^.]+)\.launchpad\.(.+)$/;

const getApiHostnameFromSiteHostname = (siteHostname: string): string => {
  const previewMatch = siteHostname.match(PREVIEW_SITE_HOSTNAME_PATTERN);

  /**
   * Preview/staging domains can look like:
   * launchpad-<id>.launchpad.apps.dev.apolo.us
   * In this case API host should be:
   * launchpad-<id>-api.apps.dev.apolo.us
   */
  if (previewMatch) {
    const appSubdomain = previewMatch[1];
    const rootDomain = previewMatch[2];

    return `${appSubdomain}-api.${rootDomain}`;
  }

  const parts = siteHostname.split('.');
  const [firstLabel, ...restLabels] = parts;

  if (!firstLabel || restLabels.length === 0) {
    return `${siteHostname}-api`;
  }

  return `${firstLabel}-api.${restLabels.join('.')}`;
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
    console.error('getSiteUrl error (likely outside request scope):', error);

    /**
     * Fallback when headers() is called outside request scope
     * This commonly happens during auth flows
     */
    const envUrl = process.env.NEXT_PUBLIC_SITE_URL!;

    // eslint-disable-next-line no-console
    console.log('Using fallback env URL:', envUrl);

    return envUrl;
  }
};

export const getServerApiUrl = async (): Promise<string> => {
  let siteUrl = await getSiteUrl();

  if (IS_LOCAL) {
    siteUrl = process.env.NEXT_PUBLIC_SITE_URL ?? '';
  }

  const url = new URL(siteUrl);
  url.hostname = getApiHostnameFromSiteHostname(url.hostname);

  return normalizeUrl(url.toString());
};
