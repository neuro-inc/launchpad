'use client';

import { useCallback, useEffect, useRef, useState } from 'react';

import {
  ImportAppRequest,
  ImportTemplateRequest,
  InstalledApp,
  Template,
  WithPagination,
} from '@typings';
import { toast } from '@features';
import { formatToCamelCase, formatToSnakeCase } from '@utils/formatters';
import { request, safeError } from '@utils/helpers';

import {
  ConfirmationModal,
  ImportAppForm,
  ImportTemplateForm,
  InstancesTable,
  TemplatesTable,
  TemplateViewEditModal,
} from '@components/Admin';
import {
  Button,
  ChaseSpinner,
  Field,
  Modal,
  ModalRef,
} from '@components/Shared';

type AdminPageProps = {
  surfaceColors?: {
    headerBgColor?: string;
    rowBgColor?: string;
    rowAltBgColor?: string;
  };
};

export const AdminPage: React.FC<AdminPageProps> = ({ surfaceColors }) => {
  // Modal refs for programmatic control
  const importTemplateModalRef = useRef<ModalRef>(null);
  const importAppModalRef = useRef<ModalRef>(null);

  const [templates, setTemplates] = useState<Template[]>([]);
  const [instances, setInstances] = useState<InstalledApp[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [loadError, setLoadError] = useState<string | null>(null);

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

  const loadAdminData = useCallback(async () => {
    setIsLoading(true);
    setLoadError(null);

    try {
      const templatesResponse = await request<WithPagination<Template>>(
        '/api/v1/apps/templates',
      );
      const nextTemplates = formatToCamelCase(
        templatesResponse.items,
      ) as Template[];

      const instancesResponse = await request<WithPagination<InstalledApp>>(
        '/api/v1/apps/instances',
      );
      const nextInstances = formatToCamelCase(
        instancesResponse.items,
      ) as InstalledApp[];

      setTemplates(nextTemplates);
      setInstances(nextInstances);
    } catch (error) {
      setTemplates([]);
      setInstances([]);
      setLoadError(error instanceof Error ? error.message : String(error));
      // eslint-disable-next-line no-console
      console.error('Error fetching admin data:', safeError(error));
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    void loadAdminData();
  }, [loadAdminData]);

  const handleRefresh = async () => {
    await loadAdminData();
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
      await loadAdminData();
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
      await loadAdminData();
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

      const importedApp = await request<InstalledApp>('/api/v1/apps/import', {
        method: 'POST',
        body: JSON.stringify(apiData),
      });

      const warnings = importedApp.warnings ?? [];

      toast.success(
        warnings.length > 0
          ? 'App imported with warnings'
          : 'App imported successfully',
      );
      warnings.forEach((warning) => {
        toast.warning(warning);
      });
      importAppModalRef.current?.close();
      await loadAdminData();
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
      await loadAdminData();
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
      await loadAdminData();
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
    <div
      id="launchpad-admin-page"
      className="launchpad-admin-page"
      data-section="admin"
    >
      {/* Header */}
      <div
        className="launchpad-admin-header mb-8 flex items-center justify-between"
        data-section="admin-header"
      >
        <h1
          id="launchpad-admin-title"
          className="launchpad-admin-title text-h2 font-bold"
        >
          Admin Panel
        </h1>
        <Button
          className="launchpad-admin-refresh-button"
          data-action="refresh-admin-data"
          onClick={handleRefresh}
          variant="primary"
        >
          Refresh Data
        </Button>
      </div>

      {/* Templates Section */}
      <section
        id="launchpad-admin-templates-section"
        className="launchpad-admin-section launchpad-admin-templates-section mb-8"
        data-section="templates"
      >
        <div className="launchpad-admin-section-header mb-4 flex items-center justify-between">
          <h2 className="launchpad-admin-section-title text-h4 font-bold">
            App Templates
          </h2>
          <Modal
            ref={importTemplateModalRef}
            content={
              <Modal.Content
                className="launchpad-admin-modal launchpad-admin-import-template-modal max-h-[90vh] w-[90vw] max-w-4xl"
                title="Import Template"
                subtitle="Add a new template to the system"
              >
                <div
                  className="launchpad-admin-modal-body py-6"
                  data-section="import-template"
                >
                  <ImportTemplateForm
                    onSubmit={handleTemplateImport}
                    onError={handleError}
                    instances={instances}
                  />
                </div>
              </Modal.Content>
            }
          >
            <Button
              className="launchpad-admin-import-template-button"
              data-action="open-import-template"
              variant="primary"
            >
              Import Template
            </Button>
          </Modal>
        </div>

        {isLoading && (
          <div
            className="launchpad-admin-loading-state launchpad-admin-templates-loading flex items-center justify-center gap-3 rounded-lg bg-white p-6 text-neural-04"
            data-section="templates-loading-state"
            data-state="loading"
          >
            <ChaseSpinner
              color="primary"
              className="launchpad-admin-loading-spinner size-5"
            />
            <span className="launchpad-admin-loading-message">
              Loading templates...
            </span>
          </div>
        )}

        {!isLoading && loadError && (
          <div
            className="launchpad-admin-error-state launchpad-admin-data-error flex flex-col items-center gap-4 rounded-lg bg-white p-6 text-center"
            data-section="admin-data-error"
            data-state="error"
          >
            <p className="launchpad-admin-error-title text-h5 text-black">
              Admin data did not load
            </p>
            <p className="launchpad-admin-error-message max-w-md text-neural-04">
              {loadError}
            </p>
            <Button
              className="launchpad-admin-retry-button h-10 px-8"
              data-action="retry-admin-data"
              onClick={loadAdminData}
            >
              Retry
            </Button>
          </div>
        )}

        {!isLoading && !loadError && (
          <TemplatesTable
            templates={templates}
            onView={handleViewTemplate}
            onEdit={handleEditTemplate}
            onDelete={handleDeleteTemplateClick}
            headerBgColor={surfaceColors?.headerBgColor}
            rowBgColor={surfaceColors?.rowBgColor}
            rowAltBgColor={surfaceColors?.rowAltBgColor}
          />
        )}
      </section>

      {/* Template View/Edit Modal */}
      {templateToViewEdit && (
        <TemplateViewEditModal
          template={templateToViewEdit.template}
          mode={templateToViewEdit.mode}
          isOpen
          onClose={handleCloseModal}
          onSubmit={handleTemplateUpdate}
          onModeChange={handleModeChange}
          instances={instances}
        />
      )}

      {/* App Instances Section */}
      <section
        id="launchpad-admin-instances-section"
        className="launchpad-admin-section launchpad-admin-instances-section mb-8"
        data-section="instances"
      >
        <div className="launchpad-admin-section-header mb-4 flex items-center justify-between">
          <h2 className="launchpad-admin-section-title text-h4 font-bold">
            App Instances
          </h2>
          <Modal
            ref={importAppModalRef}
            content={
              <Modal.Content
                className="launchpad-admin-modal launchpad-admin-import-app-modal max-h-[90vh] w-[90vw] max-w-4xl"
                title="Import App Instance"
                subtitle="Import an existing app instance into the system"
              >
                <div
                  className="launchpad-admin-modal-body py-6"
                  data-section="import-app"
                >
                  <ImportAppForm
                    onSubmit={handleAppImport}
                    onError={handleError}
                  />
                </div>
              </Modal.Content>
            }
          >
            <Button
              className="launchpad-admin-import-app-button"
              data-action="open-import-app"
              variant="primary"
            >
              Import App Instance
            </Button>
          </Modal>
        </div>

        {isLoading && (
          <div
            className="launchpad-admin-loading-state launchpad-admin-instances-loading flex items-center justify-center gap-3 rounded-lg bg-white p-6 text-neural-04"
            data-section="instances-loading-state"
            data-state="loading"
          >
            <ChaseSpinner
              color="primary"
              className="launchpad-admin-loading-spinner size-5"
            />
            <span className="launchpad-admin-loading-message">
              Loading instances...
            </span>
          </div>
        )}

        {!isLoading && !loadError && (
          <InstancesTable
            instances={instances}
            onDelete={handleDeleteInstanceClick}
            headerBgColor={surfaceColors?.headerBgColor}
            rowBgColor={surfaceColors?.rowBgColor}
            rowAltBgColor={surfaceColors?.rowAltBgColor}
          />
        )}
      </section>

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
            className="launchpad-admin-uninstall-template-checkbox text-neural-06"
            containerClassName="launchpad-admin-confirmation-option"
            data-action="toggle-uninstall-template-apps"
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
            className="launchpad-admin-uninstall-app-checkbox text-neural-06"
            containerClassName="launchpad-admin-confirmation-option"
            data-action="toggle-uninstall-app"
          >
            uninstall app
          </Field.Checkbox>
        </ConfirmationModal>
      )}
    </div>
  );
};
