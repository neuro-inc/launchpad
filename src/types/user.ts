import { UtcIsoDate } from './shared';

export namespace User {
  export type Phone = {
    phone: string;
    verifiedAt: UtcIsoDate;
  };

  export type Model = {
    email: string;
    name: string;
    phones: Phone[];
  };
}
