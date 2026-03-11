import { cn } from '@utils';

type Props = {
  className?: string;
  style?: React.CSSProperties;
  children?: React.ReactNode;
};

export const TableCell = ({ className, style, children }: Props) => (
  <td
    className={cn(
      'flex h-full shrink-0 flex-col justify-center border-t border-stroke p-4',
      className,
    )}
    style={style}
  >
    {children}
  </td>
);
