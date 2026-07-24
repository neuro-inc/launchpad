import { cn } from '@utils';

import { Logo } from '@components/Ui/Logo';

type Props = {
  className?: string;
};

export const ThemeLogo = ({ className }: Props) => {
  return <Logo className={cn('launchpad-theme-logo', className)} />;
};
