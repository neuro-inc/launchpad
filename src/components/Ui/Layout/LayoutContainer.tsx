import { cn } from '@utils';

type Props = {
  className?: string;
  children?: React.ReactNode;
};

export const LayoutContainer: React.FC<Props> = ({ className, children }) => (
  <div className={cn('mx-auto w-full max-w-[1512px] px-20', className)}>
    {children}
  </div>
);
