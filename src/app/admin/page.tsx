import { Metadata } from 'next';

import { InstalledApp, Template, WithPagination } from '@typings';
import { formatToCamelCase } from '@utils/formatters';
import { request } from '@utils/helpers';

import { Layout } from '@components/Ui';

import { AdminPage } from './AdminPage';

export const metadata: Metadata = {
  title: 'Admin Panel - Launchpad',
  description:
    'Admin panel for managing app templates and instances in Launchpad. Import and configure applications.',
  keywords: ['admin', 'management', 'templates', 'applications', 'launchpad'],
};

export default async function Page() {
  // Fetch initial data server-side
  // Note: Authentication and admin access are handled by middleware.ts
  let templates: Template[] = [];
  let instances: InstalledApp[] = [];

  try {
    // Fetch templates from /api/v1/apps/templates endpoint (returns paginated response)
    const templatesResponse = await request<WithPagination<Template>>(
      '/api/v1/apps/templates',
    );
    templates = formatToCamelCase(templatesResponse.items) as Template[];

    // Fetch instances from /api/v1/apps/instances endpoint (returns paginated response)
    try {
      const instancesResponse = await request<WithPagination<InstalledApp>>(
        '/api/v1/apps/instances',
      );
      instances = formatToCamelCase(instancesResponse.items) as InstalledApp[];
    } catch (instanceError) {
      console.error('Error fetching instances:', instanceError);
    }
  } catch (error) {
    console.error('Error fetching admin data:', error);
  }

  return (
    <Layout>
      <Layout.Container className="py-8">
        <AdminPage initialTemplates={templates} initialInstances={instances} />
      </Layout.Container>
    </Layout>
  );
}
