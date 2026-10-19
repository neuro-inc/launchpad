import Link from 'next/link';
import { Session } from 'next-auth';

import { User } from '@typings';
import { getConfig } from '@actions/server.actions';
import { cn, isObject } from '@utils';
import { isAdmin } from '@utils/helpers';

import { Render, Theme } from '@components';
import { Image } from '@components/Shared';
import { Layout } from '@components/Ui';
import { UserPanel } from '@components/Ui/UserPanel';

type HeaderSession = { user: User } | null;

type Props = {
  className?: string;
  session: Session | null;
};

export const LayoutHeader: React.FC<Props> = async ({ className, session }) => {
  const data = session as HeaderSession;
  const config = await getConfig();

  const isAuthenticated = isObject(data?.user);
  const userIsAdmin = session ? isAdmin(session) : false;

  return (
    <header id="launchpad-header" className={cn('launchpad-header', className)}>
      <Layout.Container className="launchpad-header__container flex items-center justify-between py-9">
        <Link
          href="/"
          className="launchpad-header__brand-link transition-opacity hover:opacity-75"
          data-logo={config.logoUrl ? 'custom' : 'default'}
        >
          <div className="launchpad-header__brand flex items-center gap-4">
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

            <Render
              if={
                Boolean(config.logoUrl) &&
                isAuthenticated &&
                Boolean(config.title)
              }
            >
              <p className="launchpad-header__title text-h6">{config.title}</p>
            </Render>
          </div>
        </Link>

        <Render if={isAuthenticated}>
          <UserPanel user={data?.user} isAdmin={userIsAdmin} />
        </Render>
      </Layout.Container>
    </header>
  );
};
