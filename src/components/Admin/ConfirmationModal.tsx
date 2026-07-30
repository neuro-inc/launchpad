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
    <Modal.Content
      className="launchpad-admin-modal launchpad-admin-confirmation-modal max-w-lg"
      title={title}
      description={message}
    >
      <div
        className="launchpad-admin-confirmation-body space-y-4"
        data-section="confirmation"
        data-variant={variant}
      >
        <p className="launchpad-admin-confirmation-message text-body text-neural-06">
          {message}
        </p>

        {warningMessage && (
          <div
            className="launchpad-admin-confirmation-warning flex gap-3 rounded-lg border border-error bg-error-subtle p-4"
            data-section="warning"
          >
            <Icon
              icon={faTriangleExclamation}
              className="launchpad-admin-confirmation-warning-icon mt-0.5 text-error"
              size="lg"
            />
            <p className="launchpad-admin-confirmation-warning-message text-body text-error-dark">
              {warningMessage}
            </p>
          </div>
        )}

        {children}
      </div>

      <Modal.Footer className="launchpad-admin-confirmation-footer">
        <div className="launchpad-admin-confirmation-actions flex justify-end gap-3">
          <Button
            className="launchpad-admin-confirmation-cancel"
            data-action="cancel-confirmation"
            variant="ghost"
            onClick={handleCancel}
          >
            {cancelLabel}
          </Button>
          <Button
            className="launchpad-admin-confirmation-confirm"
            data-action="confirm"
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
