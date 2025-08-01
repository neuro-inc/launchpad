import { AuthOptions } from 'next-auth';
import KeycloakProvider from 'next-auth/providers/keycloak';

import {
  KEYCLOAK_CLIENT_ID,
  KEYCLOAK_ISSUER,
  NEXTAUTH_SECRET,
} from '@constants';

export const authOptions: AuthOptions = {
  providers: [
    KeycloakProvider({
      clientId: KEYCLOAK_CLIENT_ID,
      clientSecret: '',
      issuer: KEYCLOAK_ISSUER,
    }),
  ],
  secret: NEXTAUTH_SECRET,
  session: {
    strategy: 'jwt',
  },
};
