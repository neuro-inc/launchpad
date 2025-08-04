// types/next-auth.d.ts
import { DefaultUser } from 'next-auth';

declare module 'next-auth' {
  interface Session {
    accessToken?: string;
  }

  interface User extends DefaultUser {
    accessToken?: string;
  }
}

declare module 'next-auth/jwt' {
  interface JWT {
    accessToken?: string;
  }
}
