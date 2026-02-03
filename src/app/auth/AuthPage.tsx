import { Theme } from '@components';
import { Layout } from '@components/Ui';

import { LoginButton } from './LoginButton';

export const AuthPage = async () => {
  return (
    <Layout>
      <Layout.Container className="flex flex-1 items-center justify-center">
        <Theme.Container className="flex w-full max-w-[584px] -translate-y-1/4 flex-col items-center gap-6 p-14 sm-md:p-8">
          <h2 className="text-center text-h3 sm-md:text-h4">
            Welcome to <span className="inline-block">Launchpad</span>!
          </h2>
          <LoginButton />
        </Theme.Container>
      </Layout.Container>
    </Layout>
  );
};
