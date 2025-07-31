import { Logo } from '@components/Ui/Logo';

type Props = {
  className?: string;
};

export const ThemeLogo = ({ className }: Props) => {
  return <Logo className={className} />;
};
