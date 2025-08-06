import { ImageURL } from './shared';

type AppLink = {
  text: string;
  url: string;
};

export type App = {
  name: string;
  title: string;
  descriptionShort: string;
  descriptionLong: string;
  version: string;
  logo: ImageURL;
  documentationUrls: AppLink[];
  launchpadAppName: string;
  externalUrls: AppLink[];
  tags: string[];
};

export type Instance = {
  launchpadAppName: string;
  url: string | null;
};
