/**
 * Authentication configuration is received from the server
 */
export type KeycloakConfig = {
  realm: string;
  url: string;
  idp_hint?: string | null;
};
