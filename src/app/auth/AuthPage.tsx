import { Link, Theme } from '@components';

import { LoginButton } from './LoginButton';

export const AuthPage = () => {
  return (
    <div className="relative mx-auto flex size-full flex-1 flex-col bg-background px-16 pb-6 pt-10 font-inter">
      <div className="flex items-center justify-between">
        <Theme.Logo className="h-10 w-auto text-black" />
      </div>
      <div className="relative flex flex-1 items-center justify-center">
        <Theme.Container className="flex w-full max-w-[500px] flex-col items-center gap-6 px-6 pb-6 pt-12">
          <h2 className="text-center text-h4">
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
      </div>
    </div>
  );
};
