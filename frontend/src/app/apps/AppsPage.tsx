import { getConfig } from '@actions/server.actions';
import { getBrighterColor } from '@utils/helpers';

import { Layout } from '@components/Ui';

import { AppsListClient } from './AppsListClient';

export const AppsPage: React.FC = async () => {
  const config = await getConfig();

  const appTileColor = getBrighterColor(config.background, 80);

  const appTileStyle = {
    '--launchpad-app-card-background': appTileColor || '#ffffff',
  } as React.CSSProperties;

  return (
    <Layout>
      <AppsListClient tileStyle={appTileStyle} />
    </Layout>
  );
};
