import { AnyFunction } from '@typings';
import { cn, noop } from '@utils';

type Props = {
  className?: string;
  children?: React.ReactNode;
  onClick?: AnyFunction;
  onDoubleClick?: AnyFunction;
};

export const TableRow = ({
  className,
  children,
  onClick = noop,
  onDoubleClick = noop,
}: Props) => (
  <tr
    className={cn('contents', className)}
    onClick={onClick}
    onDoubleClick={onDoubleClick}
  >
    {children}
  </tr>
);
