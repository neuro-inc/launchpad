'use client';

import { PopoverContentProps } from '@radix-ui/react-popover';
import * as PopoverUI from '@radix-ui/react-popover';

import { VariantProps } from '@typings';
import { getSlots, tv } from '@utils';

import { Button } from './Button';
import { Render } from './Render';

const variants = tv({
  base: 'z-30 rounded-lg bg-white px-3 py-4 text-body text-rebecca shadow-[0px_4px_12px_0px_rgba(0,0,0,0.12)] will-change-[transform,opacity] data-[state=closed]:duration-300 data-[state=open]:duration-300 data-[state=open]:animate-in data-[state=closed]:animate-out data-[state=closed]:fade-out data-[state=open]:fade-in',
  variants: {
    side: {
      top: 'data-[state=open]:data-[side=top]:slide-in-from-top-1 data-[state=closed]:data-[side=top]:slide-out-to-top-1',
      right:
        'data-[state=open]:data-[side=right]:slide-in-from-right-1 data-[state=closed]:data-[side=right]:slide-out-to-right-1',
      bottom:
        'data-[state=open]:data-[side=bottom]:slide-in-from-bottom-1 data-[state=closed]:data-[side=bottom]:slide-out-to-bottom-1',
      left: 'data-[state=open]:data-[side=left]:slide-in-from-left-1 data-[state=closed]:data-[side=left]:slide-out-to-left-1',
    },
  },
});

type PopperContentProps = Pick<
  PopoverContentProps,
  'align' | 'alignOffset' | 'side' | 'sideOffset'
>;

type Variants = VariantProps<typeof variants>;

type ComponentProps = {
  className?: string;
  triggerClassName?: string;
  showArrow?: boolean;
  disabled?: boolean;
  children: React.ReactNode;
};

type OpenState =
  | {
      open: boolean;
      onOpenChange: (state: boolean) => void;
    }
  | {
      open?: never;
      onOpenChange?: never;
    };

type Props = Variants & PopperContentProps & ComponentProps & OpenState;

export const Popover = ({
  className,
  triggerClassName,
  open,
  onOpenChange,
  side = 'top',
  sideOffset = 8,
  align,
  alignOffset,
  showArrow = true,
  disabled,
  children,
}: Props) => {
  const { content, trigger } = getSlots<'trigger'>(children);

  return (
    <PopoverUI.Root open={open} onOpenChange={onOpenChange}>
      <PopoverUI.Trigger asChild>
        <Button theme disabled={disabled} className={triggerClassName}>
          {trigger}
        </Button>
      </PopoverUI.Trigger>
      <PopoverUI.Portal>
        <PopoverUI.Content
          hideWhenDetached
          side={side}
          sideOffset={sideOffset}
          align={align}
          alignOffset={alignOffset}
          className={variants({ side, className })}
        >
          <div className="flex flex-col gap-2.5">{content}</div>
          <Render if={showArrow}>
            <PopoverUI.Arrow className="fill-white" />
          </Render>
        </PopoverUI.Content>
      </PopoverUI.Portal>
    </PopoverUI.Root>
  );
};

/**
 * todo: think about exporting props
 */
export type PopoverOpenStateProps = OpenState;
