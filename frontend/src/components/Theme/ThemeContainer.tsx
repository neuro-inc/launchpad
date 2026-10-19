import { cn } from '@utils';

type Props = {
  className?: string;
  children?: React.ReactNode;
};

export const ThemeContainer = ({ className, children }: Props) => (
  <div
    className={cn(
      'launchpad-theme-container rounded-2xl bg-white px-10 py-14 shadow-[0px_16px_24px_0px_rgba(0,0,0,0.08)]',
      className,
    )}
  >
    {children}
  </div>
);
