import { getServerSession } from 'next-auth';
import clsx from 'clsx';

import { getAuthOptions } from '@features';
import {
  canDeriveLaunchpadApiHostname,
  getServerApiUrl,
  getSiteUrl,
} from '@utils/helpers';

import { LayoutCookieSync } from '@components/Ui/Layout/LayoutCookieSync';

import { LayoutContainer } from './LayoutContainer';
import { LayoutHeader } from './LayoutHeader';
import { LayoutWrapper } from './LayoutWrapper';

type Props = {
  className?: string;
  children: React.ReactNode;
};

export const Layout = async ({ className, children }: Props) => {
  const siteUrl = await getSiteUrl();
  const siteHostname = new URL(siteUrl).hostname;
  const supportsLaunchpadAuth = canDeriveLaunchpadApiHostname(siteHostname);

  const authBootstrap = supportsLaunchpadAuth
    ? await (async () => {
        const authOptions = await getAuthOptions();
        const [session, apiUrl] = await Promise.all([
          getServerSession(authOptions),
          getServerApiUrl(),
        ]);

        return { session, apiUrl };
      })()
    : { session: null, apiUrl: null };

  return (
    <LayoutWrapper className="flex flex-1 flex-col">
      {authBootstrap.apiUrl && (
        <LayoutCookieSync
          token={authBootstrap.session?.accessToken}
          sessionError={authBootstrap.session?.error}
          apiUrl={authBootstrap.apiUrl}
        />
      )}
      <LayoutHeader session={authBootstrap.session} />
      <main className={clsx('flex flex-1 flex-col', className)}>
        {children}
      </main>
    </LayoutWrapper>
  );
};

Layout.Container = LayoutContainer;
Layout.Wrapper = LayoutWrapper;
