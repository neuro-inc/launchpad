import Link from 'next/link';
import { Session } from 'next-auth';

import { User } from '@typings';
import { getConfig } from '@actions/server.actions';
import { isObject } from '@utils';
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
    <header className={className}>
      <Layout.Container className="flex items-center justify-between py-9">
        <Link href="/" className="transition-opacity hover:opacity-75">
          {config.logoUrl ? (
            <div className="flex items-center gap-4">
              <div className="flex items-center">
                <Image
                  src={config.logoUrl}
                  alt="Logo"
                  height={40}
                  width={40}
                  className="h-10 w-auto object-contain"
                  style={{ width: 'auto', height: '40px' }}
                  priority
                />
              </div>

              <Render if={isAuthenticated && Boolean(config.title)}>
                <p className="text-h6">{config.title}</p>
              </Render>
            </div>
          ) : (
            <Theme.Logo className="h-10 w-auto text-black" />
          )}
        </Link>

        <Render if={isAuthenticated}>
          <UserPanel user={data?.user} isAdmin={userIsAdmin} />
        </Render>
      </Layout.Container>
    </header>
  );
};
