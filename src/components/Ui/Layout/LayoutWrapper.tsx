import { cn } from '@utils';

type Props = {
  className?: string;
  children: React.ReactNode;
};

export const LayoutWrapper: React.FC<Props> = ({ className, children }) => {
  return (
    <div className={cn('flex size-full flex-1 flex-col', className)}>
      {children}
    </div>
  );
};
