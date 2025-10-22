import React from 'react';
import { TooltipContentProps } from '@radix-ui/react-tooltip';
import * as TooltipUI from '@radix-ui/react-tooltip';

import { VariantProps } from '@typings';
import { getSlots, tv } from '@utils';

import { Render } from '@components';

const variants = tv({
  base: 'z-[60] rounded-lg bg-white px-3 py-4 text-body text-rebecca shadow-[0px_4px_12px_0px_rgba(0,0,0,0.12)] will-change-[transform,opacity] data-[state=closed]:duration-300 data-[state=delayed-open]:duration-300 data-[state=instant-open]:duration-300 data-[state=delayed-open]:animate-in data-[state=instant-open]:animate-in data-[state=closed]:animate-out data-[state=closed]:fade-out data-[state=delayed-open]:fade-in data-[state=instant-open]:fade-in',
  variants: {
    side: {
      top: 'data-[state=delayed-open]:data-[side=top]:slide-in-from-top-1 data-[state=instant-open]:data-[side=top]:slide-in-from-top-1 data-[state=closed]:data-[side=top]:slide-out-to-top-1',
      right:
        'data-[state=delayed-open]:data-[side=right]:slide-in-from-right-1 data-[state=instant-open]:data-[side=right]:slide-in-from-right-1 data-[state=closed]:data-[side=right]:slide-out-to-right-1',
      bottom:
        'data-[state=delayed-open]:data-[side=bottom]:slide-in-from-bottom-1 data-[state=instant-open]:data-[side=bottom]:slide-in-from-bottom-1 data-[state=closed]:data-[side=bottom]:slide-out-to-bottom-1',
      left: 'data-[state=delayed-open]:data-[side=left]:slide-in-from-left-1 data-[state=instant-open]:data-[side=left]:slide-in-from-left-1 data-[state=closed]:data-[side=left]:slide-out-to-left-1',
    },
  },
});

type PopoverContentProps = Pick<
  TooltipContentProps,
  'align' | 'alignOffset' | 'side' | 'sideOffset'
>;

type Variants = VariantProps<typeof variants>;

type ComponentProps = {
  disabled?: boolean;
  showArrow?: boolean;
  className?: string;
  delayDuration?: number;
  children: React.ReactNode;
};

type Props = Variants & PopoverContentProps & ComponentProps;

export const Tooltip = ({
  className,
  disabled,
  showArrow = true,
  delayDuration = 300,
  side = 'top',
  sideOffset = 8,
  align,
  alignOffset,
  children,
}: Props) => {
  const { trigger, content } = getSlots<'trigger'>(children);

  /**
   * Set `open` state to `false` if disabled,
   * otherwise `undefined` is provided
   */
  const isOpen = disabled ? false : undefined;

  return (
    <TooltipUI.Provider delayDuration={delayDuration}>
      <TooltipUI.Root open={isOpen}>
        <TooltipUI.Trigger asChild>{trigger}</TooltipUI.Trigger>
        <TooltipUI.Portal>
          <TooltipUI.Content
            className={variants({ side, className })}
            side={side}
            sideOffset={sideOffset}
            align={align}
            alignOffset={alignOffset}
          >
            {content}
            <Render if={showArrow}>
              <TooltipUI.Arrow className="fill-white" />
            </Render>
          </TooltipUI.Content>
        </TooltipUI.Portal>
      </TooltipUI.Root>
    </TooltipUI.Provider>
  );
};
