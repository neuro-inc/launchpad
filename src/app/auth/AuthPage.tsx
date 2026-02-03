import { getConfig } from '@actions/server.actions';

import { Theme } from '@components';
import { Layout } from '@components/Ui';

import { LoginButton } from './LoginButton';

export const AuthPage = async () => {
  const config = await getConfig();

  return (
    <Layout>
      <div className="flex flex-1 items-center justify-center">
        <Layout.Container className="flex w-full max-w-[584px] -translate-y-1/4 flex-col items-center gap-6 p-14 sm-md:p-8">
          <Theme.Container className="flex w-full flex-col items-center gap-6">
            <h2 className="text-center text-h3 sm-md:text-h4">
              {config.title || 'Welcome to Launchpad!'}
            </h2>
            <LoginButton />
          </Theme.Container>
        </Layout.Container>
      </div>
    </Layout>
  );
};
