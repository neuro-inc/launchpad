'use client';

import { useEffect, useRef, useState } from 'react';

import { ImportTemplateRequest, InstalledApp, Template } from '@typings';

import { Button, Modal, ModalRef, Table } from '@components/Shared';

import { ImportTemplateForm } from './ImportTemplateForm';

type TemplateViewEditModalProps = {
  template: Template | null;
  mode: 'view' | 'edit';
  isOpen: boolean;
  onClose: () => void;
  onSubmit: (data: ImportTemplateRequest) => Promise<void>;
  onModeChange: (mode: 'view' | 'edit') => void;
  instances: InstalledApp[];
};

export const TemplateViewEditModal: React.FC<TemplateViewEditModalProps> = ({
  template,
  mode,
  isOpen,
  onClose,
  onSubmit,
  onModeChange,
  instances,
}) => {
  const [error, setError] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const formRef = useRef<HTMLFormElement>(null);
  const modalRef = useRef<ModalRef>(null);

  // Control modal open/close based on isOpen prop
  useEffect(() => {
    if (isOpen) {
      modalRef.current?.open();
    } else {
      modalRef.current?.close();
    }
  }, [isOpen]);

  if (!template) return null;

  const handleSubmit = async (data: ImportTemplateRequest) => {
    try {
      setIsSubmitting(true);
      await onSubmit(data);
      onClose();
    } catch (err: any) {
      setError(err.message || 'Failed to update template');
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleError = (errorMessage: string) => {
    setError(errorMessage);
  };

  const handleEditClick = () => {
    onModeChange('edit');
  };

  const handleSaveClick = () => {
    // Trigger form submission
    if (formRef.current) {
      formRef.current.requestSubmit();
    }
  };

  const handleCancel = () => {
    if (mode === 'edit') {
      onModeChange('view');
    } else {
      onClose();
    }
  };

  // Get instances related to this template
  // Note: instance.templateName is a foreign key that refers to template.name
  const relatedInstances = instances.filter(
    (instance) => instance.templateName === template.name,
  );

  const modalContent = (
    <Modal.Content
      className="max-h-[90vh] w-[90vw] max-w-4xl"
      title={
        mode === 'view'
          ? `View Template: ${template.verboseName}`
          : `Edit Template: ${template.verboseName}`
      }
      subtitle={`${template.templateName} v${template.templateVersion}`}
    >
      <div className="py-6">
        {error && (
          <div className="mb-4 rounded-lg bg-error-light p-4 text-error-dark">
            {error}
          </div>
        )}
        <ImportTemplateForm
          ref={formRef}
          onSubmit={handleSubmit}
          onError={handleError}
          editingTemplate={template}
          onCancel={handleCancel}
          instances={instances}
          isInModal
          isReadOnly={mode === 'view'}
        />

        {/* Related Instances Section - Only show in view mode */}
        {mode === 'view' && (
          <div className="mt-8 border-t border-neural-02 pt-6">
            <h3 className="mb-4 text-h5 font-medium">
              Related App Instances ({relatedInstances.length})
            </h3>
            {relatedInstances.length === 0 ? (
              <p className="text-body text-neural-05">
                No app instances are using this template.
              </p>
            ) : (
              <div className="overflow-x-auto">
                <Table className="w-full grid-cols-[2fr_1.5fr_1fr_1fr]">
                  <Table.Header>
                    <Table.Row>
                      <Table.Head className="border-b border-neural-03 bg-neural-01 text-caption">
                        App Name
                      </Table.Head>
                      <Table.Head className="border-b border-neural-03 bg-neural-01 text-caption">
                        Launchpad Name
                      </Table.Head>
                      <Table.Head className="border-b border-neural-03 bg-neural-01 text-caption">
                        User ID
                      </Table.Head>
                      <Table.Head className="border-b border-neural-03 bg-neural-01 text-caption">
                        URL
                      </Table.Head>
                    </Table.Row>
                  </Table.Header>
                  <Table.Body>
                    {relatedInstances.map((instance, index) => (
                      <Table.Row
                        key={instance.id || `${instance.appId}-${index}`}
                      >
                        <Table.Cell className="border-b border-neural-02">
                          <div className="text-body font-medium">
                            {instance.appName}
                          </div>
                          <div className="text-caption text-neural-05">
                            ID: {instance.appId}
                          </div>
                        </Table.Cell>
                        <Table.Cell className="border-b border-neural-02">
                          <div className="text-body">
                            {instance.launchpadAppName}
                          </div>
                        </Table.Cell>
                        <Table.Cell className="border-b border-neural-02">
                          <div className="text-body text-neural-06">
                            {instance.userId || '-'}
                          </div>
                        </Table.Cell>
                        <Table.Cell className="border-b border-neural-02">
                          {instance.url ? (
                            <a
                              href={instance.url}
                              target="_blank"
                              rel="noopener noreferrer"
                              className="text-body text-primary underline hover:text-primary-dark"
                            >
                              Open
                            </a>
                          ) : (
                            <span className="text-caption text-neural-05">
                              -
                            </span>
                          )}
                        </Table.Cell>
                      </Table.Row>
                    ))}
                  </Table.Body>
                </Table>
              </div>
            )}
          </div>
        )}
      </div>
      <Modal.Footer sticky>
        <Button variant="secondary" onClick={handleCancel}>
          {mode === 'edit' ? 'Cancel' : 'Close'}
        </Button>
        {mode === 'view' ? (
          <Button variant="primary" onClick={handleEditClick}>
            Edit
          </Button>
        ) : (
          <Button
            variant="primary"
            onClick={handleSaveClick}
            disabled={isSubmitting}
          >
            {isSubmitting ? 'Saving...' : 'Save'}
          </Button>
        )}
      </Modal.Footer>
    </Modal.Content>
  );

  return (
    <Modal
      ref={modalRef}
      defaultOpen={false}
      onClose={onClose}
      content={modalContent}
    />
  );
};
