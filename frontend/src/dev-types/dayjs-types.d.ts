import { IsoDate, UtcIsoDate } from '@typings';

import 'dayjs';

declare module 'dayjs' {
  interface Dayjs {
    toIsoDate(): IsoDate;
    toUtcIsoDate(): UtcIsoDate;
  }
}
