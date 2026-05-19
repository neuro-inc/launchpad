import clsx from 'clsx';

import { cn, getCompoundSlots } from '@utils';

import { Render } from '../Render';
import { Slot } from '../Slot';

import { ModalFooter } from './ModalFooter';
import { ModalHeader } from './ModalHeader';

type Props = {
  className?: string;
  contents?: boolean;
  title?: React.ReactNode;
  subtitle?: React.ReactNode;
  children?: React.ReactNode;
};

export const ModalContent = ({
  className,
  contents,
  title,
  children,
  subtitle,
}: Props) => {
  const { content, header, footer } = getCompoundSlots(children, {
    header: ModalHeader,
    footer: ModalFooter,
  });

  return (
    <div
      className={cn(
        'relative max-w-full overflow-auto rounded-2xl bg-white',
        className,
      )}
    >
      <Slot slot={header}>
        <Render if={title}>
          <ModalHeader subtitle={subtitle}>{title}</ModalHeader>
        </Render>
      </Slot>
      <div className={clsx('px-8', { contents })}>{content}</div>
      {footer}
    </div>
  );
};
