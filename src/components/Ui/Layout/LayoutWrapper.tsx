import { cn } from '@utils';

type Props = {
  className?: string;
  style?: React.CSSProperties;
  children: React.ReactNode;
};

export const LayoutWrapper: React.FC<Props> = ({
  className,
  style,
  children,
}) => {
  return (
    <div
      className={cn('flex min-h-full w-full flex-1 flex-col', className)}
      style={style}
    >
      {children}
    </div>
  );
};
