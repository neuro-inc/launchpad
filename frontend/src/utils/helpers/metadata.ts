import { getSiteUrl } from './getSiteUrl';

export const getAbsoluteUrl = async (path: string = ''): Promise<string> => {
  const siteUrl = await getSiteUrl();
  return `${siteUrl}${path}`;
};

export const getOgImageUrl = async (
  title?: string,
  description?: string,
): Promise<string> => {
  const siteUrl = await getSiteUrl();
  const params = new URLSearchParams();

  if (title) params.set('title', title);
  if (description) params.set('description', description);

  return `${siteUrl}/api/og?${params.toString()}`;
};
