'use client';

import { useEffect, useRef } from 'react';
import { faTriangleExclamation } from '@fortawesome/pro-regular-svg-icons';

import { Button, Icon, Modal } from '@components/Shared';
import { ModalRef } from '@components/Shared/Modal/Modal';

type ConfirmationModalProps = {
  isOpen: boolean;
  title: string;
  message: string;
  warningMessage?: string;
  confirmLabel?: string;
  cancelLabel?: string;
  onConfirm: () => void;
  onCancel: () => void;
  variant?: 'danger' | 'warning' | 'default';
  children?: React.ReactNode;
};

export const ConfirmationModal: React.FC<ConfirmationModalProps> = ({
  isOpen,
  title,
  message,
  warningMessage,
  confirmLabel = 'Confirm',
  cancelLabel = 'Cancel',
  onConfirm,
  onCancel,
  variant = 'default',
  children,
}) => {
  const modalRef = useRef<ModalRef>(null);

  useEffect(() => {
    if (isOpen) {
      modalRef.current?.open();
    } else {
      modalRef.current?.close();
    }
  }, [isOpen]);

  const handleConfirm = () => {
    onConfirm();
    modalRef.current?.close();
  };

  const handleCancel = () => {
    onCancel();
    modalRef.current?.close();
  };

  const modalContent = (
    <Modal.Content className="max-w-lg" title={title}>
      <div className="space-y-4">
        <p className="text-body text-neural-06">{message}</p>

        {warningMessage && (
          <div className="flex gap-3 rounded-lg border border-error bg-error-subtle p-4">
            <Icon
              icon={faTriangleExclamation}
              className="mt-0.5 text-error"
              size="lg"
            />
            <p className="text-body text-error-dark">{warningMessage}</p>
          </div>
        )}

        {children}
      </div>

      <Modal.Footer>
        <div className="flex justify-end gap-3">
          <Button variant="ghost" onClick={handleCancel}>
            {cancelLabel}
          </Button>
          <Button
            variant={variant === 'danger' ? 'error' : 'primary'}
            onClick={handleConfirm}
          >
            {confirmLabel}
          </Button>
        </div>
      </Modal.Footer>
    </Modal.Content>
  );

  return <Modal ref={modalRef} content={modalContent} onClose={onCancel} />;
};
