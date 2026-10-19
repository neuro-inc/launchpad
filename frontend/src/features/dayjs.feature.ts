import dayjs from 'dayjs';
import utc from 'dayjs/plugin/utc';

import { IsoDate, UtcIsoDate } from '@typings';

dayjs.extend(utc);

/**
 * This is mostly for type safety.
 *
 * todo: add description
 */
const dateFormatPlugin = (_: any, dayjsClass: any) => {
  dayjsClass.prototype.toIsoDate = function toIsoDate(): IsoDate {
    return this.toISOString() as IsoDate;
  };

  dayjsClass.prototype.toUtcIsoDate = function toUtcIsoDate(): UtcIsoDate {
    return this.utc().toIsoDate() as UtcIsoDate;
  };
};

dayjs.extend(dateFormatPlugin);

export { dayjs };
