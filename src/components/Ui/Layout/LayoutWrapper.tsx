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
      className={cn(
        'flex size-full min-h-full flex-1 flex-col overflow-auto',
        className,
      )}
      style={style}
    >
      {children}
    </div>
  );
};
