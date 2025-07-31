import { cn } from '@utils';

type Props = {
  className?: string;
  children?: React.ReactNode;
};

export const TableHeader = ({ className, children }: Props) => (
  <thead className={cn('contents', className)}>{children}</thead>
);
