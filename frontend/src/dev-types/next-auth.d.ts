declare module 'next-auth' {
  interface Session {
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
