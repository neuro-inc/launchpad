const normalizeUrl = (url: string): string => url.replace(/\/$/, '');

const PREVIEW_SITE_HOSTNAME_PATTERN = /^([^.]+)\.launchpad\.(.+)$/;

export const canDeriveLaunchpadApiHostname = (
  siteHostname: string,
): boolean => {
  const parts = siteHostname.split('.');
  const [firstLabel, ...restLabels] = parts;

  return Boolean(
    firstLabel && restLabels.length > 0 && firstLabel !== 'launchpad',
  );
};

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

  if (!canDeriveLaunchpadApiHostname(siteHostname)) {
    throw new Error(
      `Cannot derive Launchpad API hostname from generic site hostname: ${siteHostname}`,
    );
  }

  return `${firstLabel}-api.${restLabels.join('.')}`;
};

export const deriveServerApiUrl = (siteUrl: string): string => {
  const url = new URL(siteUrl);

  url.hostname = getApiHostnameFromSiteHostname(url.hostname);

  /**
   * The site URL can contain a route (for example `/auth`), but backend
   * endpoints are always resolved from the API origin.
   */
  url.pathname = '/';
  url.search = '';
  url.hash = '';

  return normalizeUrl(url.toString());
};
