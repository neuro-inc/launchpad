import { AnyFunction } from '@typings';
import { cn, noop } from '@utils';

type Props = Omit<
  React.HTMLAttributes<HTMLTableRowElement>,
  'onClick' | 'onDoubleClick'
> & {
  children?: React.ReactNode;
  onClick?: AnyFunction;
  onDoubleClick?: AnyFunction;
};

export const TableRow = ({
  className,
  children,
  onClick = noop,
  onDoubleClick = noop,
  ...props
}: Props) => (
  <tr
    {...props}
    className={cn('launchpad-table__row contents', className)}
    onClick={onClick}
    onDoubleClick={onDoubleClick}
  >
    {children}
  </tr>
);
