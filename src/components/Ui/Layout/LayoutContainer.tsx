import { cn } from '@utils';

type Props = React.HTMLAttributes<HTMLDivElement>;

export const LayoutContainer: React.FC<Props> = ({
  className,
  children,
  ...props
}) => (
  <div
    {...props}
    className={cn(
      'launchpad-container mx-auto w-full max-w-[1512px] px-20 hd:px-16 sm-md:px-4',
      className,
    )}
  >
    {children}
  </div>
);
