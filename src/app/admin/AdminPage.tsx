'use client';

import { useRef, useState } from 'react';
import { useRouter } from 'next/navigation';

import {
  ImportAppRequest,
  ImportTemplateRequest,
  InstalledApp,
  Template,
} from '@typings';
import { toast } from '@features';
import { formatToSnakeCase } from '@utils/formatters';
import { request } from '@utils/helpers';

import {
  ConfirmationModal,
  ImportAppForm,
  ImportTemplateForm,
  InstancesTable,
  TemplatesTable,
  TemplateViewEditModal,
} from '@components/Admin';
import { Button, Field, Modal, ModalRef } from '@components/Shared';

type AdminPageProps = {
  initialTemplates: Template[];
  initialInstances: InstalledApp[];
  surfaceColors?: {
    headerBgColor?: string;
    rowBgColor?: string;
    rowAltBgColor?: string;
  };
};

export const AdminPage: React.FC<AdminPageProps> = ({
  initialTemplates,
  initialInstances,
  surfaceColors,
}) => {
  const router = useRouter();

  // Modal refs for programmatic control
  const importTemplateModalRef = useRef<ModalRef>(null);
  const importAppModalRef = useRef<ModalRef>(null);

  // Template view/edit modal - store only the template and mode, not open/close state
  const [templateToViewEdit, setTemplateToViewEdit] = useState<{
    template: Template;
    mode: 'view' | 'edit';
  } | null>(null);

  // Delete confirmation - store only the item to delete, not open/close state
  const [templateToDelete, setTemplateToDelete] = useState<Template | null>(
    null,
  );
  const [instanceToDelete, setInstanceToDelete] = useState<InstalledApp | null>(
    null,
  );
  const [uninstallTemplate, setUninstallTemplate] = useState(true);
  const [uninstallApp, setUninstallApp] = useState(true);

  const handleRefresh = () => {
    router.refresh();
    toast.success('Data refreshed successfully');
  };

  const handleTemplateImport = async (data: ImportTemplateRequest) => {
    try {
      // Convert camelCase to snake_case for API
      const apiData = formatToSnakeCase(data);

      await request('/api/v1/apps/templates/import', {
        method: 'POST',
        body: JSON.stringify(apiData),
      });

      toast.success('Template imported successfully');
      importTemplateModalRef.current?.close();
      router.refresh();
    } catch (error: any) {
      toast.error(error.message || 'Failed to import template');
      throw error;
    }
  };

  const handleTemplateUpdate = async (data: ImportTemplateRequest) => {
    try {
      // Convert camelCase to snake_case for API
      const apiData = formatToSnakeCase(data);

      await request('/api/v1/apps/templates/import', {
        method: 'POST',
        body: JSON.stringify(apiData),
      });

      toast.success('Template updated successfully');
      setTemplateToViewEdit(null);
      router.refresh();
    } catch (error: any) {
      toast.error(error.message || 'Failed to update template');
      throw error;
    }
  };

  const handleViewTemplate = (template: Template) => {
    setTemplateToViewEdit({ template, mode: 'view' });
  };

  const handleEditTemplate = (template: Template) => {
    setTemplateToViewEdit({ template, mode: 'edit' });
  };

  const handleCloseModal = () => {
    setTemplateToViewEdit(null);
  };

  const handleModeChange = (mode: 'view' | 'edit') => {
    setTemplateToViewEdit((prev) => (prev ? { ...prev, mode } : null));
  };

  const handleAppImport = async (data: ImportAppRequest) => {
    try {
      // Convert camelCase to snake_case for API
      const apiData = formatToSnakeCase(data);

      await request('/api/v1/apps/import', {
        method: 'POST',
        body: JSON.stringify(apiData),
      });

      toast.success('App imported successfully');
      importAppModalRef.current?.close();
      router.refresh();
    } catch (error: any) {
      toast.error(error.message || 'Failed to import app');
      throw error;
    }
  };

  const handleError = (error: string) => {
    toast.error(error);
  };

  const confirmDeleteTemplate = async () => {
    if (!templateToDelete) return;

    try {
      const uninstallValue = uninstallTemplate ? 'True' : 'False';

      await request(
        `/api/v1/apps/templates/${templateToDelete.id}?uninstall=${uninstallValue}`,
        {
          method: 'DELETE',
        },
      );

      toast.success('Template deleted successfully');
      setTemplateToDelete(null);
      setUninstallTemplate(true);
      router.refresh();
    } catch (error: any) {
      toast.error(error.message || 'Failed to delete template');
    }
  };

  const confirmDeleteInstance = async () => {
    if (!instanceToDelete) return;

    const { appId } = instanceToDelete;

    if (!appId) {
      toast.error('App ID is missing. Cannot delete instance.');
      return;
    }

    try {
      const uninstallValue = uninstallApp ? 'True' : 'False';

      await request(
        `/api/v1/apps/instances/${appId}?uninstall=${uninstallValue}`,
        {
          method: 'DELETE',
        },
      );

      toast.success('App instance deleted successfully');
      setInstanceToDelete(null);
      setUninstallApp(true);
      router.refresh();
    } catch (error: any) {
      toast.error(error.message || 'Failed to delete app instance');
    }
  };

  const handleDeleteInstanceClick = (instance: InstalledApp) => {
    setUninstallApp(true);
    setInstanceToDelete(instance);
  };

  const handleDeleteTemplateClick = (template: Template) => {
    setUninstallTemplate(true);
    setTemplateToDelete(template);
  };

  const handleCancelDeleteTemplate = () => {
    setTemplateToDelete(null);
    setUninstallTemplate(true);
  };

  const handleCancelDeleteInstance = () => {
    setInstanceToDelete(null);
    setUninstallApp(true);
  };

  return (
    <>
      {/* Header */}
      <div className="mb-8 flex items-center justify-between">
        <h1 className="text-h2 font-bold">Admin Panel</h1>
        <Button onClick={handleRefresh} variant="primary">
          Refresh Data
        </Button>
      </div>

      {/* Templates Section */}
      <div className="mb-8">
        <div className="mb-4 flex items-center justify-between">
          <h2 className="text-h4 font-bold">App Templates</h2>
          <Modal
            ref={importTemplateModalRef}
            content={
              <Modal.Content
                className="max-h-[90vh] w-[90vw] max-w-4xl"
                title="Import Template"
                subtitle="Add a new template to the system"
              >
                <div className="py-6">
                  <ImportTemplateForm
                    onSubmit={handleTemplateImport}
                    onError={handleError}
                    instances={initialInstances}
                  />
                </div>
              </Modal.Content>
            }
          >
            <Button variant="primary">Import Template</Button>
          </Modal>
        </div>

        <TemplatesTable
          templates={initialTemplates}
          onView={handleViewTemplate}
          onEdit={handleEditTemplate}
          onDelete={handleDeleteTemplateClick}
          headerBgColor={surfaceColors?.headerBgColor}
          rowBgColor={surfaceColors?.rowBgColor}
          rowAltBgColor={surfaceColors?.rowAltBgColor}
        />
      </div>

      {/* Template View/Edit Modal */}
      {templateToViewEdit && (
        <TemplateViewEditModal
          template={templateToViewEdit.template}
          mode={templateToViewEdit.mode}
          isOpen
          onClose={handleCloseModal}
          onSubmit={handleTemplateUpdate}
          onModeChange={handleModeChange}
          instances={initialInstances}
        />
      )}

      {/* App Instances Section */}
      <div className="mb-8">
        <div className="mb-4 flex items-center justify-between">
          <h2 className="text-h4 font-bold">App Instances</h2>
          <Modal
            ref={importAppModalRef}
            content={
              <Modal.Content
                className="max-h-[90vh] w-[90vw] max-w-4xl"
                title="Import App Instance"
                subtitle="Import an existing app instance into the system"
              >
                <div className="py-6">
                  <ImportAppForm
                    onSubmit={handleAppImport}
                    onError={handleError}
                  />
                </div>
              </Modal.Content>
            }
          >
            <Button variant="primary">Import App Instance</Button>
          </Modal>
        </div>

        <InstancesTable
          instances={initialInstances}
          onDelete={handleDeleteInstanceClick}
          headerBgColor={surfaceColors?.headerBgColor}
          rowBgColor={surfaceColors?.rowBgColor}
          rowAltBgColor={surfaceColors?.rowAltBgColor}
        />
      </div>

      {/* Delete Template Confirmation Modal */}
      {templateToDelete && (
        <ConfirmationModal
          isOpen
          title="Delete Template"
          message={`Are you sure you want to delete the template "${templateToDelete.verboseName || templateToDelete.name}"?`}
          warningMessage={`WARNING: All app instances using this template will be deleted${uninstallTemplate ? ' and uninstalled' : ''}. This action cannot be undone.`}
          confirmLabel="Delete Template"
          cancelLabel="Cancel"
          variant="danger"
          onConfirm={confirmDeleteTemplate}
          onCancel={handleCancelDeleteTemplate}
        >
          <Field.Checkbox
            name="uninstallTemplate"
            checked={uninstallTemplate}
            onChange={(event) => setUninstallTemplate(event.target.checked)}
            className="text-neural-06"
          >
            uninstall related apps
          </Field.Checkbox>
        </ConfirmationModal>
      )}

      {/* Delete Instance Confirmation Modal */}
      {instanceToDelete && (
        <ConfirmationModal
          isOpen
          title="Delete App Instance"
          message={`Are you sure you want to delete the app instance "${instanceToDelete.launchpadAppName || instanceToDelete.appName}"?`}
          warningMessage="This will uninstall the app and remove all associated data. This action cannot be undone."
          confirmLabel="Delete Instance"
          cancelLabel="Cancel"
          variant="danger"
          onConfirm={confirmDeleteInstance}
          onCancel={handleCancelDeleteInstance}
        >
          <Field.Checkbox
            name="uninstallApp"
            checked={uninstallApp}
            onChange={(event) => setUninstallApp(event.target.checked)}
            className="text-neural-06"
          >
            uninstall app
          </Field.Checkbox>
        </ConfirmationModal>
      )}
    </>
  );
};
