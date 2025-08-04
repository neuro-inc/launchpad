import { ImageURL } from './shared';

type AppLink = {
  text: string;
  url: string;
};

export type App = {
  name: string;
  title: string;
  shortDescription: string;
  description: string;
  version: string;
  logo: ImageURL;
  documentationUrls: AppLink[];
  externalUrls: AppLink[];
  tags: string[];
};
