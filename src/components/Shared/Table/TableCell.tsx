import { cn } from '@utils';

type Props = {
  className?: string;
  children?: React.ReactNode;
};

export const TableCell = ({ className, children }: Props) => (
  <td
    className={cn(
      'flex h-full shrink-0 flex-col justify-center border-t border-stroke p-4',
      className,
    )}
  >
    {children}
  </td>
);
