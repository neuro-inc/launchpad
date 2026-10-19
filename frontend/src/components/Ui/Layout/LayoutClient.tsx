'use client';

import clsx from 'clsx';

import { LayoutHeaderClient } from './LayoutHeaderClient';
import { LayoutWrapper } from './LayoutWrapper';

type Props = {
  className?: string;
  children: React.ReactNode;
};

export const LayoutClient = ({ className, children }: Props) => {
  return (
    <LayoutWrapper className="launchpad-layout flex flex-1 flex-col">
      <LayoutHeaderClient />
      <main
        id="launchpad-main"
        className={clsx('launchpad-main flex flex-1 flex-col', className)}
      >
        {children}
      </main>
    </LayoutWrapper>
  );
};
