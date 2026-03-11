import { cn } from '@utils';

import { TableBody } from './TableBody';
import { TableCell } from './TableCell';
import { TableHead } from './TableHead';
import { TableHeader } from './TableHeader';
import { TableRow } from './TableRow';

type Props = {
  className?: string;
  children?: React.ReactNode;
};

export const Table = ({ className, children }: Props) => (
  <table
    className={cn(
      'grid border-collapse overflow-hidden rounded-lg bg-white',
      className,
    )}
  >
    {children}
  </table>
);

Table.Body = TableBody;
Table.Cell = TableCell;
Table.Head = TableHead;
Table.Header = TableHeader;
Table.Row = TableRow;
