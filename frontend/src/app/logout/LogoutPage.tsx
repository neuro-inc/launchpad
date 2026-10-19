import { getServerApiUrl, getSiteUrl } from '@utils/helpers';

import { LogoutPageClient } from './LogoutPageClient';

export const LogoutPage = async () => {
  const siteUrl = await getSiteUrl();
  const apiUrl = await getServerApiUrl();

  return <LogoutPageClient apiUrl={apiUrl} returnTo={siteUrl} />;
};
