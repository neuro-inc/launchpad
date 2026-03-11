import { Metadata } from 'next';
import { Inter } from 'next/font/google';
import { NuqsAdapter } from 'nuqs/adapters/next/app';

import { getConfig } from '@actions/server.actions';
import { getBackgroundStyle } from '@utils/helpers';

import { ToastContainer } from '@components/Ui/Toast';

import '@features/dayjs.feature';

import '@fortawesome/fontawesome-svg-core/styles.css';
import './globals.css';

export const metadata: Metadata = {
  title: {
    default: 'Launchpad',
    template: '%s | Launchpad',
  },
  description:
    'Launchpad - Your gateway to cloud-native application management. Deploy, monitor, and scale applications with ease.',
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
    title: 'Launchpad',
    description:
      'Your gateway to cloud-native application management. Deploy, monitor, and scale applications with ease.',
    siteName: 'Launchpad',
  },
  twitter: {
    card: 'summary_large_image',
    title: 'Launchpad',
    description:
      'Your gateway to cloud-native application management. Deploy, monitor, and scale applications with ease.',
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
};

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

  return (
    <html
      lang="en"
      className="bg-background"
      style={backgroundStyle}
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
        className={inter.className}
        style={backgroundStyle}
        suppressHydrationWarning
      >
        <NuqsAdapter>{children}</NuqsAdapter>
        <ToastContainer />
      </body>
    </html>
  );
}
