import { Metadata } from 'next';

import { getConfig } from '@actions/server.actions';
import { getBrighterColor } from '@utils/helpers';

import { Layout } from '@components/Ui';

import { AdminPage } from './AdminPage';

export const metadata: Metadata = {
  title: 'Admin Panel - Launchpad',
  description:
    'Admin panel for managing app templates and instances in Launchpad. Import and configure applications.',
  keywords: ['admin', 'management', 'templates', 'applications', 'launchpad'],
};

export default async function Page() {
  const config = await getConfig();

  const surfaceColors = {
    headerBgColor: getBrighterColor(config.background, 72),
    rowBgColor: getBrighterColor(config.background, 92),
    rowAltBgColor: getBrighterColor(config.background, 82),
  };

  return (
    <Layout>
      <Layout.Container className="launchpad-admin-page-container py-8">
        <AdminPage surfaceColors={surfaceColors} />
      </Layout.Container>
    </Layout>
  );
}
