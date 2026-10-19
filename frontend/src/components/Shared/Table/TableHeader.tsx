import { cn } from '@utils';

type Props = React.HTMLAttributes<HTMLTableSectionElement> & {
  children?: React.ReactNode;
};

export const TableHeader = ({ className, children, ...props }: Props) => (
  <thead
    {...props}
    className={cn('launchpad-table__header contents', className)}
  >
    {children}
  </thead>
);
