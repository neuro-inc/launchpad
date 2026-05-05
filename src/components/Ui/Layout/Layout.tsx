import { getServerSession } from 'next-auth';
import clsx from 'clsx';

import { getAuthOptions } from '@features';

import { LayoutCookieSync } from '@components/Ui/Layout/LayoutCookieSync';

import { LayoutContainer } from './LayoutContainer';
import { LayoutHeader } from './LayoutHeader';
import { LayoutWrapper } from './LayoutWrapper';

type Props = {
  className?: string;
  children: React.ReactNode;
};

export const Layout = async ({ className, children }: Props) => {
  const authOptions = await getAuthOptions();
  const session = await getServerSession(authOptions);

  return (
    <LayoutWrapper className="flex flex-1 flex-col">
      <LayoutCookieSync token={session?.accessToken} />
      <LayoutHeader />
      <main className={clsx('flex flex-1 flex-col', className)}>
        {children}
      </main>
    </LayoutWrapper>
  );
};

Layout.Container = LayoutContainer;
Layout.Wrapper = LayoutWrapper;
