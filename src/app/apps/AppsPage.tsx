import { getConfig } from '@actions/server.actions';
import { getBrighterColor } from '@utils/helpers';

import { Layout } from '@components/Ui';

import { AppsListClient } from './AppsListClient';

export const AppsPage: React.FC = async () => {
  const config = await getConfig();

  const appTileColor = getBrighterColor(config.background, 80);

  const appTileStyle = appTileColor
    ? ({ backgroundColor: appTileColor } as React.CSSProperties)
    : undefined;

  return (
    <Layout>
      <AppsListClient tileStyle={appTileStyle} />
    </Layout>
  );
};
