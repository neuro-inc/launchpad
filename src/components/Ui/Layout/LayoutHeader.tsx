import { getServerSession } from 'next-auth';

import { User } from '@typings';
import { getAuthOptions } from '@features';
import { isObject } from '@utils';

import { Render, Theme } from '@components';
import { Layout } from '@components/Ui';
import { UserPanel } from '@components/Ui/UserPanel';

type Session = { user: User } | null;

type Props = {
  className?: string;
};

export const LayoutHeader: React.FC<Props> = async ({ className }) => {
  const authOptions = await getAuthOptions();
  const data = (await getServerSession(authOptions)) as Session;

  const isAuthenticated = isObject(data?.user);

  return (
    <header className={className}>
      <Layout.Container className="flex items-center justify-between py-9">
        <Theme.Logo className="h-10 w-auto text-black" />
        <Render if={isAuthenticated}>
          <UserPanel user={data?.user} />
        </Render>
      </Layout.Container>
    </header>
  );
};
