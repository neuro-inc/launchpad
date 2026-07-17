'use client';

import { useSession } from 'next-auth/react';

import { User } from '@typings';
import { useConfig } from '@hooks/useConfig';
import { cn, isObject } from '@utils';
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
    <header id="launchpad-header" className={cn('launchpad-header', className)}>
      <Layout.Container className="launchpad-header__container flex items-center justify-between py-9">
        <div
          className="launchpad-header__brand flex items-center gap-3"
          data-logo={config.logoUrl ? 'custom' : 'default'}
        >
          <div className="launchpad-header__logo-wrapper flex items-center">
            {config.logoUrl ? (
              <Image
                src={config.logoUrl}
                alt="Logo"
                height={40}
                width={40}
                className="launchpad-header__logo h-10 w-auto object-contain"
                priority
              />
            ) : (
              <Theme.Logo className="launchpad-header__logo launchpad-header__logo--default h-10 w-auto text-black" />
            )}
          </div>

          <Render if={!!config.title}>
            <p className="launchpad-header__title text-h6">{config.title}</p>
          </Render>
        </div>

        <Render if={isAuthenticated}>
          <UserPanel user={data?.user} isAdmin={userIsAdmin} />
        </Render>
      </Layout.Container>
    </header>
  );
};
