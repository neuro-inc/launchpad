import { App, WithPagination } from '@typings';
import { getConfig } from '@actions/server.actions';
import { formatToCamelCase } from '@utils/formatters';
import { getBrighterColor, request } from '@utils/helpers';

import { AppItem } from '@components/Apps/AppItem';
import { Layout } from '@components/Ui';

export const AppsPage: React.FC = async () => {
  const config = await getConfig();
  let apps: App[] = [];

  try {
    const { items } = await request<WithPagination<App>>('/api/v1/apps');

    apps = formatToCamelCase(items) as App[];
  } catch (error) {
    /**
     * Continue regardless of error
     */
  }

  const appTileColor = getBrighterColor(config.background, 80);

  const appTileStyle = appTileColor
    ? ({ backgroundColor: appTileColor } as React.CSSProperties)
    : undefined;

  const makeApp = (app: App) => {
    return <AppItem key={app.title} app={app} tileStyle={appTileStyle} />;
  };

  return (
    <Layout>
      <Layout.Container className="grid grid-cols-3 gap-6 pb-10 sm:grid-cols-1 md:grid-cols-2 hd:gap-4">
        {apps.map(makeApp)}
      </Layout.Container>
    </Layout>
  );
};
