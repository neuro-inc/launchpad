import { App, WithPagination } from '@typings';
import { formatToCamelCase } from '@utils/formatters';
import { request } from '@utils/helpers';

import { AppItem } from '@components/Apps/AppItem';
import { Layout } from '@components/Ui';

export const AppsPage: React.FC = async () => {
  let apps: App[] = [];

  try {
    const { items } = await request<WithPagination<App>>('/api/v1/apps');

    apps = formatToCamelCase(items) as App[];
  } catch (error) {
    /**
     * Continue regardless of error
     */
  }

  const makeApp = (app: App) => {
    return <AppItem key={app.title} app={app} />;
  };

  return (
    <Layout>
      <Layout.Container className="grid grid-cols-3 gap-6 pb-10 sm:grid-cols-1 md:grid-cols-2 hd:gap-4">
        {apps.map(makeApp)}
      </Layout.Container>
    </Layout>
  );
};
