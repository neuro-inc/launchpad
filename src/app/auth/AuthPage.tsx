import { getConfig } from '@actions/server.actions';

import { Theme } from '@components';
import { Layout } from '@components/Ui';

import { LoginButton } from './LoginButton';

export const AuthPage = async () => {
  const config = await getConfig();

  return (
    <Layout>
      <div
        id="launchpad-auth-page"
        className="launchpad-auth-page flex flex-1 items-center justify-center"
        data-page="auth"
      >
        <Layout.Container className="launchpad-auth-page__content flex w-full max-w-[584px] -translate-y-1/4 flex-col items-center gap-6 p-14 sm-md:p-8">
          <Theme.Container className="launchpad-auth-page__card flex w-full flex-col items-center gap-6">
            <h2 className="launchpad-auth-page__title text-center text-h3 sm-md:text-h4">
              {config.title || 'Welcome to Launchpad!'}
            </h2>
            <LoginButton />
          </Theme.Container>
        </Layout.Container>
      </div>
    </Layout>
  );
};
