'use client';

import {
  Children,
  cloneElement,
  forwardRef,
  RefObject,
  useCallback,
  useImperativeHandle,
  useState,
} from 'react';
import * as Dialog from '@radix-ui/react-dialog';
import { faXmark } from '@fortawesome/pro-regular-svg-icons';

import { cn, noop } from '@utils';

import { Button, Icon } from '@components';

import { ModalContent } from './ModalContent';
import { ModalFooter } from './ModalFooter';
import { ModalHeader } from './ModalHeader';

export type ModalRef = {
  open: () => void;
  close: () => void;
};

type Props = {
  className?: string;
  disabled?: boolean;
  defaultOpen?: boolean;
  showCloseButton?: boolean;
  preventOutsideClick?: boolean;
  content?: React.ReactElement;
  /**
   * Modal trigger
   */
  children?: React.ReactElement;
  /**
   * Portal container
   */
  containerRef?: RefObject<HTMLElement>;
  onOpen?: (...args: unknown[]) => void;
  onClose?: (...args: unknown[]) => void;
};

const ModalComponent = forwardRef<ModalRef, Props>(
  (
    {
      className,
      disabled,
      defaultOpen = false,
      showCloseButton = true,
      preventOutsideClick = false,
      content,
      children,
      containerRef,
      onOpen = noop,
      onClose = noop,
    },
    ref,
  ) => {
    const [open, setOpen] = useState(defaultOpen);

    const isOpen = !disabled && open;

    const handleOpen = useCallback(
      (...args: unknown[]) => {
        setOpen(true);
        onOpen?.(...args);
      },
      [onOpen],
    );

    const handleClose = useCallback(
      (...args: unknown[]) => {
        onClose?.(...args);

        setOpen(false);
      },
      [onClose],
    );

    const handleOpenChange = (isOpen: boolean) => {
      if (isOpen) {
        handleOpen();
      } else {
        handleClose();
      }
    };

    const handlePointerDownOutside = (event: Event) => {
      if (preventOutsideClick) {
        event.preventDefault();
      }
    };

    useImperativeHandle(
      ref,
      () => ({
        open: handleOpen,
        close: handleClose,
      }),
      [handleOpen, handleClose],
    );

    return (
      <Dialog.Root open={isOpen} onOpenChange={handleOpenChange}>
        {children && (
          <Dialog.Trigger asChild disabled={disabled}>
            {children}
          </Dialog.Trigger>
        )}
        <Dialog.Portal container={containerRef?.current}>
          <Dialog.Overlay className="fixed inset-0 z-40 bg-black/50 data-[state=open]:animate-in data-[state=closed]:animate-out data-[state=closed]:fade-out data-[state=open]:fade-in" />
          <Dialog.Content
            onPointerDownOutside={handlePointerDownOutside}
            className={cn(
              'fixed left-1/2 top-1/2 z-50 flex max-h-full max-w-full -translate-x-1/2 -translate-y-1/2 p-2 outline-none data-[state=closed]:animate-modal-out data-[state=open]:animate-modal-in',
              className,
            )}
          >
            {Children.map(content, (child) =>
              cloneElement(child as React.ReactElement<any>, {
                closeModal: handleClose,
              }),
            )}
            {showCloseButton && (
              <Dialog.Close asChild onClick={handleClose}>
                <Button
                  theme
                  className="absolute right-7 top-7 z-30 text-[20px] text-neural-03 outline-none transition-colors hover:text-black"
                >
                  <Icon icon={faXmark} />
                </Button>
              </Dialog.Close>
            )}
          </Dialog.Content>
        </Dialog.Portal>
      </Dialog.Root>
    );
  },
);

export const Modal = Object.assign(ModalComponent, {
  Content: ModalContent,
  Header: ModalHeader,
  Footer: ModalFooter,
});
