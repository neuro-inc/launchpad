import { useEffect, useRef, useState } from 'react';
import * as Dialog from '@radix-ui/react-dialog';

import { cn, getSlots } from '@utils';

import { Render } from '../Render';
import { Slot } from '../Slot';

type Props = {
  subtitle?: React.ReactNode;
  className?: string;
  sticky?: boolean;
  children?: React.ReactNode;
};

export const ModalHeader = ({
  subtitle,
  className,
  sticky,
  children,
}: Props) => {
  const [isPinned, setPinned] = useState(false);
  const ref = useRef<HTMLDivElement>(null);

  const slots = getSlots<'subtitle'>(children);

  useEffect(() => {
    if (!sticky) {
      return;
    }

    const observer = new IntersectionObserver(
      (events) => {
        const [event] = events;

        setPinned(event.intersectionRatio < 1);
      },
      { threshold: [1] },
    );

    if (ref.current) {
      observer.observe(ref.current);
    }

    return () => {
      observer.disconnect();
    };
  }, [sticky]);

  return (
    <Dialog.Title asChild>
      <h2
        className={cn(
          'launchpad-modal__header launchpad-modal__title p-8 text-h4',
          className,
          {
            'sticky -top-px z-30 border-b transition-colors border-transparent bg-inherit before:absolute before:bg-gradient-to-b before:from-white before:h-20 before:inset-x-0 before:top-full before:translate-y-px before:pointer-events-none before:opacity-0 before:transition-opacity':
              sticky,
            'border-neural-02 before:opacity-100': isPinned,
          },
        )}
        ref={ref}
        data-pinned={isPinned || undefined}
        data-sticky={sticky || undefined}
      >
        {children}

        <Slot slot={slots.subtitle}>
          <Render if={subtitle}>
            <span className="launchpad-modal__subtitle mt-1 block text-sm font-normal text-neural-04">
              {subtitle}
            </span>
          </Render>
        </Slot>
      </h2>
    </Dialog.Title>
  );
};
