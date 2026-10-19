import { Metadata } from 'next';

import { AppPage } from './AppPage';

type Props = {
  params: Promise<{
    appName: string;
  }>;
};

export async function generateMetadata({ params }: Props): Promise<Metadata> {
  const { appName } = await params;
  const formattedAppName = decodeURIComponent(appName)
    .split('-')
    .map((word) => word.charAt(0).toUpperCase() + word.slice(1))
    .join(' ');

  return {
    title: `${formattedAppName} - Launchpad`,
    description: `Access and manage ${formattedAppName} application through Launchpad. Monitor, configure, and deploy your application with ease.`,
    keywords: [
      'application',
      'app',
      formattedAppName.toLowerCase(),
      'launchpad',
      'management',
      'monitoring',
      'deployment',
    ],
  };
}

export default AppPage;
