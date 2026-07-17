import { cn } from '@utils';

type Props = React.HTMLAttributes<HTMLTableSectionElement> & {
  children?: React.ReactNode;
};

export const TableBody = ({ className, children, ...props }: Props) => (
  <tbody {...props} className={cn('launchpad-table__body contents', className)}>
    {children}
  </tbody>
);
