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
      className="launchpad-admin-modal launchpad-admin-template-details-modal max-h-[90vh] w-[90vw] max-w-4xl"
      title={
        mode === 'view'
          ? `View Template: ${template.verboseName}`
          : `Edit Template: ${template.verboseName}`
      }
      subtitle={`${template.templateName} v${template.templateVersion}`}
    >
      <div
        className="launchpad-admin-template-details-body py-6"
        data-section="template-details"
        data-mode={mode}
        data-record-id={template.id}
        data-record-name={template.name}
      >
        {error && (
          <div
            className="launchpad-admin-form-error mb-4 rounded-lg bg-error-light p-4 text-error-dark"
            data-state="error"
          >
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
          <section
            className="launchpad-admin-related-instances mt-8 border-t border-neural-02 pt-6"
            data-section="related-instances"
          >
            <h3 className="launchpad-admin-related-instances-title mb-4 text-h5 font-medium">
              Related App Instances ({relatedInstances.length})
            </h3>
            {relatedInstances.length === 0 ? (
              <p
                className="launchpad-admin-empty-state launchpad-admin-related-instances-empty text-body text-neural-05"
                data-state="empty"
              >
                No app instances are using this template.
              </p>
            ) : (
              <div className="launchpad-admin-table-wrapper launchpad-admin-related-instances-table-wrapper overflow-x-auto">
                <Table className="launchpad-admin-table launchpad-admin-related-instances-table w-full grid-cols-[2fr_1.5fr_1fr_1fr]">
                  <Table.Header className="launchpad-admin-table-header">
                    <Table.Row className="launchpad-admin-table-header-row">
                      <Table.Head
                        className="launchpad-admin-table-header-cell launchpad-admin-column-app-name border-b border-neural-03 bg-neural-01 text-caption"
                        data-column="app-name"
                      >
                        App Name
                      </Table.Head>
                      <Table.Head
                        className="launchpad-admin-table-header-cell launchpad-admin-column-launchpad-name border-b border-neural-03 bg-neural-01 text-caption"
                        data-column="launchpad-name"
                      >
                        Launchpad Name
                      </Table.Head>
                      <Table.Head
                        className="launchpad-admin-table-header-cell launchpad-admin-column-user-id border-b border-neural-03 bg-neural-01 text-caption"
                        data-column="user-id"
                      >
                        User ID
                      </Table.Head>
                      <Table.Head
                        className="launchpad-admin-table-header-cell launchpad-admin-column-url border-b border-neural-03 bg-neural-01 text-caption"
                        data-column="url"
                      >
                        URL
                      </Table.Head>
                    </Table.Row>
                  </Table.Header>
                  <Table.Body className="launchpad-admin-table-body launchpad-admin-related-instances-table-body">
                    {relatedInstances.map((instance, index) => {
                      const recordId = instance.id || instance.appId || index;

                      return (
                        <Table.Row
                          key={instance.id || `${instance.appId}-${index}`}
                          className="launchpad-admin-table-row launchpad-admin-related-instance-row contents"
                          data-record-id={recordId}
                          data-record-name={
                            instance.launchpadAppName || instance.appName
                          }
                          data-record-type="instance"
                        >
                          <Table.Cell
                            className="launchpad-admin-table-cell launchpad-admin-related-instance-cell launchpad-admin-related-instance-cell-app-name border-b border-neural-02"
                            data-column="app-name"
                          >
                            <div className="launchpad-admin-cell-content">
                              <div className="launchpad-admin-instance-app-name text-body font-medium">
                                {instance.appName}
                              </div>
                              <div className="launchpad-admin-instance-app-id text-caption text-neural-05">
                                ID: {instance.appId}
                              </div>
                            </div>
                          </Table.Cell>
                          <Table.Cell
                            className="launchpad-admin-table-cell launchpad-admin-related-instance-cell launchpad-admin-related-instance-cell-launchpad-name border-b border-neural-02"
                            data-column="launchpad-name"
                          >
                            <div className="launchpad-admin-cell-content launchpad-admin-instance-launchpad-name text-body">
                              {instance.launchpadAppName}
                            </div>
                          </Table.Cell>
                          <Table.Cell
                            className="launchpad-admin-table-cell launchpad-admin-related-instance-cell launchpad-admin-related-instance-cell-user-id border-b border-neural-02"
                            data-column="user-id"
                          >
                            <div className="launchpad-admin-cell-content launchpad-admin-instance-user-id text-body text-neural-06">
                              {instance.userId || '-'}
                            </div>
                          </Table.Cell>
                          <Table.Cell
                            className="launchpad-admin-table-cell launchpad-admin-related-instance-cell launchpad-admin-related-instance-cell-url border-b border-neural-02"
                            data-column="url"
                          >
                            <div className="launchpad-admin-cell-content">
                              {instance.url ? (
                                <a
                                  href={instance.url}
                                  target="_blank"
                                  rel="noopener noreferrer"
                                  className="launchpad-admin-instance-link text-body text-primary underline hover:text-primary-dark"
                                  data-action="open-instance"
                                  data-record-id={recordId}
                                >
                                  Open
                                </a>
                              ) : (
                                <span className="text-caption text-neural-05">
                                  -
                                </span>
                              )}
                            </div>
                          </Table.Cell>
                        </Table.Row>
                      );
                    })}
                  </Table.Body>
                </Table>
              </div>
            )}
          </section>
        )}
      </div>
      <Modal.Footer className="launchpad-admin-template-details-footer" sticky>
        <Button
          className="launchpad-admin-template-details-cancel"
          data-action={
            mode === 'edit' ? 'cancel-template-edit' : 'close-template'
          }
          variant="secondary"
          onClick={handleCancel}
        >
          {mode === 'edit' ? 'Cancel' : 'Close'}
        </Button>
        {mode === 'view' ? (
          <Button
            className="launchpad-admin-template-details-edit"
            data-action="edit-template"
            variant="primary"
            onClick={handleEditClick}
          >
            Edit
          </Button>
        ) : (
          <Button
            className="launchpad-admin-template-details-save"
            data-action="save-template"
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
