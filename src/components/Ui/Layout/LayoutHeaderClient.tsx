'use client';

import { useSession } from 'next-auth/react';

import { User } from '@typings';
import { useConfig } from '@hooks/useConfig';
import { isObject } from '@utils';
import { isAdmin } from '@utils/helpers';

import { Render, Theme } from '@components';
import { Image } from '@components/Shared';
import { Layout } from '@components/Ui';
import { UserPanel } from '@components/Ui/UserPanel';

type Session = { user: User } | null;

type Props = {
  className?: string;
};

export const LayoutHeaderClient: React.FC<Props> = ({ className }) => {
  const { data: session } = useSession();
  const data = session as Session;
  const config = useConfig();

  const isAuthenticated = isObject(data?.user);
  const userIsAdmin = session ? isAdmin(session) : false;

  return (
    <header className={className}>
      <Layout.Container className="flex items-center justify-between py-9">
        <div className="flex items-center gap-3">
          {config.logoUrl ? (
            <Image
              src={config.logoUrl}
              alt="Logo"
              height={40}
              width={0}
              className="h-10 w-auto object-contain"
              style={{ width: 'auto', height: '40px' }}
              priority
            />
          ) : (
            <Theme.Logo className="h-10 w-auto text-black" />
          )}

          <Render if={!!config.title}>
            <p className="text-h6">{config.title}</p>
          </Render>
        </div>

        <Render if={isAuthenticated}>
          <UserPanel user={data?.user} isAdmin={userIsAdmin} />
        </Render>
      </Layout.Container>
    </header>
  );
};
