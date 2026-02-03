import clsx from 'clsx';

import { LayoutContainer } from './LayoutContainer';
import { LayoutHeader } from './LayoutHeader';
import { LayoutWrapper } from './LayoutWrapper';

type Props = {
  className?: string;
  children: React.ReactNode;
};

export const Layout = ({ className, children }: Props) => {
  return (
    <LayoutWrapper className="flex flex-1 flex-col">
      <LayoutHeader />
      <main className={clsx('flex flex-1 flex-col', className)}>
        {children}
      </main>
    </LayoutWrapper>
  );
};

Layout.Container = LayoutContainer;
Layout.Wrapper = LayoutWrapper;
