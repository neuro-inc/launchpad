import { KeycloakConfig } from '@typings';

export const getKeycloakIssuer = ({ realm, url }: KeycloakConfig) => {
  return `${url}/realms/${realm}`;
};
