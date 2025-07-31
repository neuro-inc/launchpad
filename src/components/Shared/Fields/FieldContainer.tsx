import { cn } from '@utils';

type Props = {
  className?: string;
  children?: React.ReactNode;
};

export const FieldContainer: React.FC<Props> = ({ className, children }) => {
  return <div className={cn('relative', className)}>{children}</div>;
};

FieldContainer.displayName = 'Field.Container';
