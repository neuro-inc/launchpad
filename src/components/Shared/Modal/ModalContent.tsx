import clsx from 'clsx';

import { cn, getCompoundSlots } from '@utils';

import { Modal, Render, Slot } from '@components';

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
    header: Modal.Header,
    footer: Modal.Footer,
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
          <Modal.Header subtitle={subtitle}>{title}</Modal.Header>
        </Render>
      </Slot>
      <div className={clsx('px-8', { contents })}>{content}</div>
      {footer}
    </div>
  );
};
