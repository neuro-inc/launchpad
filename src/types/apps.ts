/**
 * Base properties shared between App and Template types
 */
type BaseAppProperties = {
  name: string;
  descriptionShort: string;
  descriptionLong: string;
  logo: string;
  documentationUrls: Array<{ [key: string]: string }>;
  externalUrls: Array<{ [key: string]: string }>;
  tags: string[];
  position?: number | null;
};

export type UpdateTemplateOrderRequest = {
  templateIds: string[];
};

export type App = BaseAppProperties & {
  title: string;
  version: string;
  launchpadAppName: string;
};

export type Instance = {
  launchpadAppName: string;
  url: string | null;
};

/**
 * Admin-specific app types
 */

// Template type matches LaunchpadTemplateRead from /api/v1/apps/templates
export type Template = BaseAppProperties & {
  id: string;
  templateName: string;
  templateVersion: string;
  verboseName: string;
  isInternal: boolean;
  isShared: boolean;
  input: Record<string, any>;
};

export type InstalledApp = {
  id: string;
  appId: string;
  appName: string;
  launchpadAppName: string;
  isInternal: boolean;
  isShared: boolean;
  userId: string | null;
  url: string | null;
  templateName: string;
  warnings?: string[];
};

export type UnimportedInstance = {
  id: string;
  name: string;
  templateName: string;
  templateVersion: string;
  displayName: string;
  state: string;
  createdAt: string;
  endpoints: string[];
};

/**
 * Admin API request types
 */

export type ImportTemplateRequest = {
  templateName: string;
  templateVersion: string;
  name?: string | null;
  verboseName?: string | null;
  descriptionShort?: string | null;
  descriptionLong?: string | null;
  logo?: string | null;
  documentationUrls?: Array<{ [key: string]: string }> | null;
  externalUrls?: Array<{ [key: string]: string }> | null;
  tags?: string[] | null;
  isInternal?: boolean;
  isShared?: boolean;
  input?: Record<string, any>;
};

export type ImportAppRequest = {
  appId: string;
  name?: string | null;
  verboseName?: string | null;
  descriptionShort?: string | null;
  descriptionLong?: string | null;
  logo?: string | null;
  documentationUrls?: Array<{ [key: string]: string }> | null;
  externalUrls?: Array<{ [key: string]: string }> | null;
  tags?: string[] | null;
  isInternal?: boolean;
};
