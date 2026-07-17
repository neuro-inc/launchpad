import { cn } from '@utils';

type Props = React.HTMLAttributes<HTMLDivElement> & {
  children: React.ReactNode;
};

export const LayoutWrapper: React.FC<Props> = ({
  className,
  children,
  ...props
}) => {
  return (
    <div
      {...props}
      className={cn(
        'launchpad-layout-wrapper flex size-full min-h-full flex-1 flex-col overflow-auto',
        className,
      )}
    >
      {children}
    </div>
  );
};
