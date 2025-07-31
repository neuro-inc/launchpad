import { useEffect, useRef, useState } from 'react';

import { cn } from '@utils';

type Props = {
  className?: string;
  sticky?: boolean;
  children?: React.ReactNode;
};

export const ModalFooter = ({ className, sticky, children }: Props) => {
  const [isPinned, setPinned] = useState(false);
  const ref = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!sticky) {
      return;
    }

    const observer = new IntersectionObserver(
      ([event]) => setPinned(event.intersectionRatio < 1),
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
    <div
      ref={ref}
      className={cn('flex justify-end gap-4 p-8', className, {
        'sticky -bottom-px z-30 transition-colors border-t border-transparent bg-inherit before:absolute before:bg-gradient-to-t before:from-white before:h-20 before:inset-x-0 before:bottom-full before:-translate-y-px before:pointer-events-none before:opacity-0 before:transition-opacity':
          sticky,
        'border-neural-02 before:opacity-100': isPinned,
      })}
    >
      {children}
    </div>
  );
};
