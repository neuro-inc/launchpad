import clsx from 'clsx';

import { getConfig } from '@actions/server.actions';

import { LayoutContainer } from './LayoutContainer';
import { LayoutHeader } from './LayoutHeader';
import { LayoutWrapper } from './LayoutWrapper';

type Props = {
  className?: string;
  children: React.ReactNode;
};

export const Layout = async ({ className, children }: Props) => {
  const config = await getConfig();

  return (
    <LayoutWrapper
      className="flex flex-1 flex-col"
      style={
        config.background ? { backgroundColor: config.background } : undefined
      }
    >
      <LayoutHeader />
      <main className={clsx('flex flex-1 flex-col', className)}>
        {children}
      </main>
    </LayoutWrapper>
  );
};

Layout.Container = LayoutContainer;
Layout.Wrapper = LayoutWrapper;
