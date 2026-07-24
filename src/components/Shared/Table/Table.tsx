import { cn } from '@utils';

import { TableBody } from './TableBody';
import { TableCell } from './TableCell';
import { TableHead } from './TableHead';
import { TableHeader } from './TableHeader';
import { TableRow } from './TableRow';

type Props = React.TableHTMLAttributes<HTMLTableElement> & {
  children?: React.ReactNode;
};

export const Table = ({ className, children, ...props }: Props) => (
  <table
    {...props}
    className={cn(
      'launchpad-table grid border-collapse overflow-hidden rounded-lg bg-white',
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
