import { cn } from '@utils';

import { Render } from '../Render';

type Props = {
  className?: string;
  children?: React.ReactNode;
};

export const FieldNote = ({ className, children }: Props) => (
  <Render if={children}>
    <p
      className={cn(
        'launchpad-field__note mt-2 w-full pl-2 text-caption text-neural-04',
        className,
      )}
    >
      {children}
    </p>
  </Render>
);

FieldNote.displayName = 'Field.Note';
