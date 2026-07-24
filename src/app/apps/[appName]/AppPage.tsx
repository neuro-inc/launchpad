import { Poppins } from 'next/font/google';
import clsx from 'clsx';

import { App } from '@typings';

import { Layout } from '@components/Ui';
import { Logo } from '@components/Ui/Logo';

import { AppWatcher } from './AppWatcher';
import './styles.css';

const poppins = Poppins({
  weight: ['600'],
  subsets: ['latin'],
});

type Params = {
  appName: App['launchpadAppName'];
};

type Props = {
  params: Promise<Params>;
};

export const AppPage: React.FC<Props> = async ({ params }) => {
  const { appName } = await params;

  return (
    <>
      <AppWatcher appName={appName} />
      <Layout.Wrapper
        id="launchpad-app-loading-page"
        className="launchpad-app-loading-page"
        data-app-name={appName}
        data-page="app-loading"
      >
        <main
          id="launchpad-main"
          className="launchpad-app-loading-page__content launchpad-main flex flex-1 flex-col items-center justify-center"
        >
          <Logo.Icon className="launchpad-app-loading-page__logo size-[48px]" />
          <p
            className={clsx(
              'launchpad-app-loading-page__brand mt-4 text-[32px] font-600 leading-[30px]',
              poppins.className,
            )}
          >
            Launchpad
          </p>
          <p className="launchpad-app-loading-page__message mt-2.5 flex items-end text-body-medium">
            The app will start soon{' '}
            <span className="launchpad-app-loading-page__dots dot-flashing text-[10px]" />
          </p>
        </main>
      </Layout.Wrapper>
    </>
  );
};
