import { Metadata } from 'next';
import { Inter } from 'next/font/google';
import { NuqsAdapter } from 'nuqs/adapters/next/app';

import { ToastContainer } from '@components/Ui/Toast';

import '@features/dayjs.feature';

import '@fortawesome/fontawesome-svg-core/styles.css';
import './globals.css';

export const metadata: Metadata = {
  title: 'Apolo Launchpad',
};

const inter = Inter({
  weight: ['400', '500', '600', '700', '800'],
  subsets: ['latin'],
});

type Props = {
  children: React.ReactNode;
};

export default async function RootLayout({ children }: Props) {
  return (
    <html lang="en">
      <body className={inter.className}>
        <NuqsAdapter>{children}</NuqsAdapter>
        <ToastContainer />
      </body>
    </html>
  );
}
