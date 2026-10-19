import { IconProp } from '@fortawesome/fontawesome-svg-core';
import {
  FontAwesomeIcon,
  FontAwesomeIconProps,
} from '@fortawesome/react-fontawesome';

import { cn } from '@utils';

type Props = Omit<FontAwesomeIconProps, 'icon'> & {
  icon?: IconProp | null;
  className?: string;
};

export const Icon = ({ className, icon, ...props }: Props) => {
  if (!icon) {
    return null;
  }

  return (
    <span
      className={cn(
        'launchpad-icon flex size-6 shrink-0 items-center justify-center',
        className,
      )}
    >
      <FontAwesomeIcon {...props} icon={icon} />
    </span>
  );
};
