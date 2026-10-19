import { Metadata } from 'next';
import { Inter } from 'next/font/google';
import { NuqsAdapter } from 'nuqs/adapters/next/app';

import { getConfig } from '@actions/server.actions';
import { cn } from '@utils';
import { getBackgroundStyle } from '@utils/helpers';

import { ToastContainer } from '@components/Ui/Toast';

import '@features/dayjs.feature';

import { AppVersionLog } from './AppVersionLog';
import '@fortawesome/fontawesome-svg-core/styles.css';
import './globals.css';

export const dynamic = 'force-dynamic';
export const runtime = 'nodejs';

export async function generateMetadata(): Promise<Metadata> {
  const config = await getConfig();

  const title = config.title || 'Launchpad';
  const description =
    'Your gateway to cloud-native application management. Deploy, monitor, and scale applications with ease.';

  return {
    title: {
      default: title,
      template: `%s | ${title}`,
    },
    description,
    keywords: [
      'launchpad',
      'kubernetes',
      'cloud-native',
      'applications',
      'deployment',
      'monitoring',
      'development',
    ],
    authors: [{ name: 'Apolo' }],
    creator: 'Apolo',
    publisher: 'Apolo',
    formatDetection: {
      email: false,
      address: false,
      telephone: false,
    },
    openGraph: {
      type: 'website',
      locale: 'en_US',
      title,
      description,
      siteName: title,
    },
    twitter: {
      card: 'summary_large_image',
      title,
      description,
    },
    robots: {
      index: true,
      follow: true,
      googleBot: {
        index: true,
        follow: true,
        'max-video-preview': -1,
        'max-image-preview': 'large',
        'max-snippet': -1,
      },
    },
    ...(config.faviconUrl && {
      icons: {
        icon: config.faviconUrl,
        shortcut: config.faviconUrl,
        apple: config.faviconUrl,
      },
    }),
  };
}

const inter = Inter({
  weight: ['400', '500', '600', '700', '800'],
  subsets: ['latin'],
});

type Props = {
  children: React.ReactNode;
};

export default async function RootLayout({ children }: Props) {
  const config = await getConfig();
  const backgroundStyle = getBackgroundStyle(config.background);
  const hasImageBackground = Boolean(backgroundStyle?.backgroundImage);
  const backgroundVariables = backgroundStyle
    ? ({
        '--launchpad-background': backgroundStyle.background,
        '--launchpad-background-image': backgroundStyle.backgroundImage,
        '--launchpad-background-size': backgroundStyle.backgroundSize,
        '--launchpad-background-position': backgroundStyle.backgroundPosition,
        '--launchpad-background-repeat': backgroundStyle.backgroundRepeat,
      } as React.CSSProperties)
    : undefined;

  return (
    <html
      id="launchpad-root"
      lang="en"
      className={cn('launchpad-root', {
        'launchpad-background--image': hasImageBackground,
      })}
      style={backgroundVariables}
      suppressHydrationWarning
    >
      <head>
        {config.faviconUrl && (
          <>
            <link rel="icon" href={config.faviconUrl} />
            <link rel="shortcut icon" href={config.faviconUrl} />
            <link rel="apple-touch-icon" href={config.faviconUrl} />
            <meta name="theme-color" content={config.background || '#ffffff'} />
          </>
        )}
      </head>
      <body
        id="launchpad-body"
        className={cn(inter.className, 'launchpad-body overflow-hidden', {
          'launchpad-background--image': hasImageBackground,
        })}
        suppressHydrationWarning
      >
        <AppVersionLog />
        <NuqsAdapter>{children}</NuqsAdapter>
        <ToastContainer />
        {config.cssUrl && (
          <link
            id="launchpad-custom-stylesheet"
            rel="stylesheet"
            href={config.cssUrl}
            precedence="launchpad-custom"
          />
        )}
      </body>
    </html>
  );
}
