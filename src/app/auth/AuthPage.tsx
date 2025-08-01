import { Link, Theme } from '@components';
import { Layout } from '@components/Ui';

import { LoginButton } from './LoginButton';

export const AuthPage = () => {
  return (
    <Layout>
      <Layout.Container className="flex flex-1 items-center justify-center">
        <Theme.Container className="flex w-full max-w-[584px] flex-col items-center gap-6 p-14 pb-10">
          <h2 className="text-center text-h3">
            Welcome to <span className="inline-block">Launchpad</span>!
          </h2>
          <LoginButton />
          <p className="-mt-2 text-neural-04">
            Don&apos;t have an account?
            <Link variant="ghost-primary" href="/signup" className="px-2">
              Sign up
            </Link>
          </p>
        </Theme.Container>
      </Layout.Container>
    </Layout>
  );
};
