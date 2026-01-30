import { Metadata } from 'next';
import { redirect } from 'next/navigation';
import { getServerSession } from 'next-auth';

import { InstalledApp, Template, WithPagination } from '@typings';
import { PATH } from '@constants';
import { getAuthOptions } from '@features';
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
  // Server-side admin access check
  const authOptions = await getAuthOptions();
  const session = await getServerSession(authOptions);

  if (!session) {
    redirect(PATH.AUTH);
  }

  const clientRoles = (session.client_roles as string[]) || [];
  const realmRoles = (session.realm_roles as string[]) || [];
  const roles = clientRoles.length > 0 ? clientRoles : realmRoles;
  const isAdmin = roles.includes('admin');

  if (!isAdmin) {
    redirect(PATH.APPS);
  }

  // Fetch initial data server-side
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
