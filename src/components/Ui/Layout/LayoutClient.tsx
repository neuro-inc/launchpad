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
    <LayoutWrapper className="flex flex-1 flex-col">
      <LayoutHeaderClient />
      <main className={clsx('flex flex-1 flex-col', className)}>
        {children}
      </main>
    </LayoutWrapper>
  );
};
