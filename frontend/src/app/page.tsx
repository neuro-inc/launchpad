import { Metadata } from 'next';

import { AppsPage } from './apps/AppsPage';

export const metadata: Metadata = {
  title: 'Apps - Launchpad',
  description:
    'Browse and access your applications through Launchpad. Manage your development and production environments with ease.',
  keywords: ['launchpad', 'apps', 'applications', 'development', 'kubernetes'],
};

export default AppsPage;
