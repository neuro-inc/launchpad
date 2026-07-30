'use client';

import { useCallback, useEffect, useRef, useState } from 'react';
import {
  faArrowsRotate,
  faCubesStacked,
  faLayerGroup,
  faPlus,
} from '@fortawesome/pro-regular-svg-icons';

import {
  ImportAppRequest,
  ImportTemplateRequest,
  InstalledApp,
  Template,
  UpdateTemplateOrderRequest,
  WithPagination,
} from '@typings';
import { toast } from '@features';
import { formatToCamelCase, formatToSnakeCase } from '@utils/formatters';
import { request, safeError, sortByPosition } from '@utils/helpers';

import {
  AppsOrderModal,
  ConfirmationModal,
  ImportAppForm,
  ImportTemplateForm,
  InstancesTable,
  TemplatesTable,
  TemplateViewEditModal,
} from '@components/Admin';
import { Button, Field, Icon, Modal, ModalRef } from '@components/Shared';

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

      setTemplates(sortByPosition(nextTemplates));
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

  const handleSaveTemplateOrder = async (templateIds: string[]) => {
    const previousTemplates = templates;
    const templatesById = new Map(
      templates.map((template) => [template.id, template]),
    );
    const orderedVisibleTemplates = templateIds
      .map((id) => templatesById.get(id))
      .filter((template): template is Template => Boolean(template));
    const internalTemplates = templates.filter(
      (template) => template.isInternal,
    );

    setTemplates([...orderedVisibleTemplates, ...internalTemplates]);

    try {
      const payload: UpdateTemplateOrderRequest = { templateIds };

      await request('/api/v1/apps/templates/order', {
        method: 'PUT',
        body: JSON.stringify(formatToSnakeCase(payload)),
      });

      toast.success('Launchpad app order saved');
    } catch (error: any) {
      setTemplates(previousTemplates);
      toast.error(error.message || 'Failed to save app order');
      throw error;
    }
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
        className="launchpad-admin-header mb-8 flex items-start justify-between gap-6 sm:flex-col"
        data-section="admin-header"
      >
        <div className="launchpad-admin-heading">
          <h1
            id="launchpad-admin-title"
            className="launchpad-admin-title text-h3 font-bold sm:text-h4"
          >
            Admin Panel
          </h1>
          <p className="launchpad-admin-description mt-2 max-w-2xl text-body text-neural-04">
            Manage application templates and imported instances from one place.
          </p>
        </div>
        <Button
          className="launchpad-admin-refresh-button h-10 shrink-0 px-4 sm:w-full"
          data-action="refresh-admin-data"
          onClick={handleRefresh}
          variant="secondary"
          disabled={isLoading}
        >
          <Icon
            icon={faArrowsRotate}
            className={isLoading ? 'animate-spin' : undefined}
          />
          Refresh
        </Button>
      </div>

      {!isLoading && loadError && (
        <div
          className="launchpad-admin-error-state launchpad-admin-data-error mb-6 flex items-center justify-between gap-5 rounded-xl border border-error/20 bg-error-subtle px-5 py-4 sm:flex-col sm:items-start"
          data-section="admin-data-error"
          data-state="error"
        >
          <div>
            <p className="launchpad-admin-error-title text-h7 text-error-dark">
              Admin data did not load
            </p>
            <p className="launchpad-admin-error-message mt-1 text-body-medium text-neural-05">
              {loadError}
            </p>
          </div>
          <Button
            className="launchpad-admin-retry-button h-9 shrink-0 px-4 sm:w-full"
            data-action="retry-admin-data"
            onClick={loadAdminData}
            variant="error-outline"
          >
            Try again
          </Button>
        </div>
      )}

      {/* Templates Section */}
      <section
        id="launchpad-admin-templates-section"
        className="launchpad-admin-section launchpad-admin-templates-section mb-10 overflow-hidden rounded-2xl border border-neural-02 bg-white/80 shadow-[0_8px_30px_rgba(19,26,57,0.06)]"
        data-section="templates"
      >
        <div className="launchpad-admin-section-header flex items-center justify-between gap-5 border-b border-neural-02 px-6 py-5 sm:flex-col sm:items-stretch sm:px-4">
          <div className="flex min-w-0 items-center gap-4">
            <div className="flex size-11 shrink-0 items-center justify-center rounded-xl bg-primary-subtle text-primary-dark">
              <Icon icon={faLayerGroup} />
            </div>
            <div className="min-w-0">
              <div className="flex items-center gap-2">
                <h2 className="launchpad-admin-section-title text-h5 font-600 sm:text-h6">
                  App Templates
                </h2>
                <span className="rounded-full bg-neural-01 px-2.5 py-1 text-caption font-600 text-neural-05">
                  {isLoading ? '—' : templates.length}
                </span>
              </div>
              <p className="mt-0.5 text-body-medium text-neural-04">
                Reusable definitions available for application deployment.
              </p>
            </div>
          </div>
          <div className="flex shrink-0 items-center gap-2 sm:flex-col">
            <AppsOrderModal
              templates={templates}
              onSave={handleSaveTemplateOrder}
            />
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
                className="launchpad-admin-import-template-button h-10 shrink-0 px-4 sm:w-full"
                data-action="open-import-template"
                variant="primary"
                icon={faPlus}
              >
                Import Template
              </Button>
            </Modal>
          </div>
        </div>

        {!loadError && (
          <TemplatesTable
            templates={templates}
            isLoading={isLoading}
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
        className="launchpad-admin-section launchpad-admin-instances-section mb-8 overflow-hidden rounded-2xl border border-neural-02 bg-white/80 shadow-[0_8px_30px_rgba(19,26,57,0.06)]"
        data-section="instances"
      >
        <div className="launchpad-admin-section-header flex items-center justify-between gap-5 border-b border-neural-02 px-6 py-5 sm:flex-col sm:items-stretch sm:px-4">
          <div className="flex min-w-0 items-center gap-4">
            <div className="flex size-11 shrink-0 items-center justify-center rounded-xl bg-secondary-subtle text-secondary-dark">
              <Icon icon={faCubesStacked} />
            </div>
            <div className="min-w-0">
              <div className="flex items-center gap-2">
                <h2 className="launchpad-admin-section-title text-h5 font-600 sm:text-h6">
                  App Instances
                </h2>
                <span className="rounded-full bg-neural-01 px-2.5 py-1 text-caption font-600 text-neural-05">
                  {isLoading ? '—' : instances.length}
                </span>
              </div>
              <p className="mt-0.5 text-body-medium text-neural-04">
                Applications currently registered with this Launchpad.
              </p>
            </div>
          </div>
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
              className="launchpad-admin-import-app-button h-10 shrink-0 px-4 sm:w-full"
              data-action="open-import-app"
              variant="primary"
              icon={faPlus}
            >
              Import App Instance
            </Button>
          </Modal>
        </div>

        {!loadError && (
          <InstancesTable
            instances={instances}
            isLoading={isLoading}
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
