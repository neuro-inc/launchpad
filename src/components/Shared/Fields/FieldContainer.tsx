import { cn } from '@utils';

type Props = React.HTMLAttributes<HTMLDivElement> & {
  children?: React.ReactNode;
};

export const FieldContainer: React.FC<Props> = ({
  className,
  children,
  ...props
}) => {
  return (
    <div {...props} className={cn('launchpad-field relative', className)}>
      {children}
    </div>
  );
};

FieldContainer.displayName = 'Field.Container';
