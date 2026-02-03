'use client';

import { useSession } from 'next-auth/react';

import { User } from '@typings';
import { isObject } from '@utils';
import { isAdmin } from '@utils/helpers';

import { Render, Theme } from '@components';
import { Layout } from '@components/Ui';
import { UserPanel } from '@components/Ui/UserPanel';

type Session = { user: User } | null;

type Props = {
  className?: string;
};

export const LayoutHeaderClient: React.FC<Props> = ({ className }) => {
  const { data: session } = useSession();
  const data = session as Session;

  const isAuthenticated = isObject(data?.user);
  const userIsAdmin = session ? isAdmin(session) : false;

  return (
    <header className={className}>
      <Layout.Container className="flex items-center justify-between py-9">
        <Theme.Logo className="h-10 w-auto text-black" />
        <Render if={isAuthenticated}>
          <UserPanel user={data?.user} isAdmin={userIsAdmin} />
        </Render>
      </Layout.Container>
    </header>
  );
};
