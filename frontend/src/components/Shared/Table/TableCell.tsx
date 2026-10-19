import { cn } from '@utils';

type Props = React.TdHTMLAttributes<HTMLTableCellElement> & {
  children?: React.ReactNode;
};

export const TableCell = ({ className, style, children, ...props }: Props) => (
  <td
    {...props}
    className={cn(
      'launchpad-table__cell flex h-full shrink-0 flex-col justify-center border-t border-stroke p-4',
      className,
    )}
    style={style}
  >
    {children}
  </td>
);
