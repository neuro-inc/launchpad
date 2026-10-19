import { getServerApiUrl, getSiteUrl } from './getSiteUrl';

/**
 * Get the site URL dynamically (for use in server components, middleware, etc.)
 * Use this when you need runtime URL detection
 */
export const getDynamicSiteUrl = async (): Promise<string> => {
  return getSiteUrl();
};

/**
 * Get the server API URL dynamically (for use in server components, middleware, etc.)
 * Use this when you need runtime URL detection
 */
export const getDynamicServerApiUrl = async (): Promise<string> => {
  return getServerApiUrl();
};

/**
 * Get both URLs at once for efficiency
 */
export const getDynamicUrls = async (): Promise<{
  siteUrl: string;
  serverApiUrl: string;
}> => {
  const siteUrl = await getSiteUrl();
  const serverApiUrl = await getServerApiUrl();

  return { siteUrl, serverApiUrl };
};
