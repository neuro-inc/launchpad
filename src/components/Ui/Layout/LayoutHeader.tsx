import Link from 'next/link';
import { getServerSession } from 'next-auth';

import { User } from '@typings';
import { getAuthOptions } from '@features';
import { isObject } from '@utils';
import { isAdmin } from '@utils/helpers';

import { Render, Theme } from '@components';
import { Layout } from '@components/Ui';
import { UserPanel } from '@components/Ui/UserPanel';

type Session = { user: User } | null;

type Props = {
  className?: string;
};

export const LayoutHeader: React.FC<Props> = async ({ className }) => {
  const authOptions = await getAuthOptions();
  const session = await getServerSession(authOptions);
  const data = session as Session;

  const isAuthenticated = isObject(data?.user);
  const userIsAdmin = session ? isAdmin(session) : false;

  return (
    <header className={className}>
      <Layout.Container className="flex items-center justify-between py-9">
        <Link href="/" className="transition-opacity hover:opacity-75">
          <Theme.Logo className="h-10 w-auto text-black" />
        </Link>
        <Render if={isAuthenticated}>
          <UserPanel user={data?.user} isAdmin={userIsAdmin} />
        </Render>
      </Layout.Container>
    </header>
  );
};
