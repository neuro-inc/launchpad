import { cn } from '@utils';

type Props = {
  className?: string;
  children?: React.ReactNode;
};

export const TableBody = ({ className, children }: Props) => (
  <tbody className={cn('contents', className)}>{children}</tbody>
);
