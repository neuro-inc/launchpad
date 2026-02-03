declare module 'next-auth' {
  interface Session {
    // Tokens are NOT included in session to keep cookie size small
    // They are stored in JWT (server-side only) and accessed via getToken()
    error?: string;
    realm_roles?: string[];
    client_roles?: string[];
  }
}

declare module 'next-auth/jwt' {
  interface JWT {
    accessToken?: string;
    idToken?: string;
    accessTokenExpires?: number;
    refreshToken?: string;
    error?: string;
    groups?: string[];
    realm_roles?: string[];
    client_roles?: string[];
  }
}

export {};
