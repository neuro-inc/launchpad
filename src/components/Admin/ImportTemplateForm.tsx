'use client';

import { forwardRef, useEffect, useMemo, useState } from 'react';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';

import { ImportTemplateRequest, InstalledApp, Template } from '@typings';
import { cn } from '@utils';
import { parseTags, tagsToString } from '@utils/helpers';

import { Button, Field } from '@components/Shared';

import { FileUpload } from './FileUpload';
import { ImportTemplateFormData, importTemplateSchema } from './schemas';

type ImportTemplateFormProps = {
  onSubmit: (data: ImportTemplateRequest) => Promise<void>;
  onError: (error: string) => void;
  editingTemplate?: Template | null;
  onCancel?: () => void;
  instances: InstalledApp[];
  isInModal?: boolean;
  isReadOnly?: boolean;
};

export const ImportTemplateForm = forwardRef<
  HTMLFormElement,
  ImportTemplateFormProps
>(
  (
    {
      onSubmit,
      onError,
      editingTemplate,
      onCancel,
      instances,
      isInModal = false,
      isReadOnly: isReadOnlyProp = false,
    },
    ref,
  ) => {
    const [mode, setMode] = useState<'manual' | 'file'>('manual');
    const [loading, setLoading] = useState(false);
    const [isEditMode, setIsEditMode] = useState(false);

    const {
      register,
      handleSubmit: handleFormSubmit,
      formState: { errors },
      reset,
      setValue,
    } = useForm<ImportTemplateFormData>({
      resolver: zodResolver(importTemplateSchema),
      defaultValues: {
        templateName: '',
        templateVersion: '',
        name: '',
        verboseName: '',
        descriptionShort: '',
        descriptionLong: '',
        logo: '',
        tags: '',
        isInternal: false,
        isShared: true,
        input: '',
      },
    });

    // Check if the current template has associated instances
    const templateHasInstances = useMemo(() => {
      if (!editingTemplate) return false;
      return instances.some(
        (instance) => instance.templateName === editingTemplate.name,
      );
    }, [editingTemplate, instances]);

    // Populate form when editing a template
    useEffect(() => {
      if (editingTemplate) {
        setValue('templateName', editingTemplate.templateName);
        setValue('templateVersion', editingTemplate.templateVersion);
        setValue('name', editingTemplate.name || '');
        setValue('verboseName', editingTemplate.verboseName || '');
        setValue('descriptionShort', editingTemplate.descriptionShort || '');
        setValue('descriptionLong', editingTemplate.descriptionLong || '');
        setValue('logo', editingTemplate.logo || '');
        setValue('tags', tagsToString(editingTemplate.tags));
        setValue('isInternal', editingTemplate.isInternal);
        setValue('isShared', editingTemplate.isShared);

        // Populate input text area if it exists
        if (
          editingTemplate.input &&
          Object.keys(editingTemplate.input).length > 0
        ) {
          setValue('input', JSON.stringify(editingTemplate.input, null, 2));
        } else {
          setValue('input', '');
        }

        // When viewing a template, start in read-only mode
        setIsEditMode(false);
      } else {
        // When creating new template, start in edit mode
        setIsEditMode(false);
        // Reset form when not editing
        reset();
      }
      // eslint-disable-next-line react-hooks/exhaustive-deps
    }, [editingTemplate]);

    const handleFileDataParsed = (data: any) => {
      setValue('templateName', data.template_name || '');
      setValue('templateVersion', data.template_version || '');
      setValue('name', data.name || '');
      setValue('verboseName', data.verbose_name || '');
      setValue('descriptionShort', data.description_short || '');
      setValue('descriptionLong', data.description_long || '');
      setValue('logo', data.logo || '');
      setValue('tags', tagsToString(data.tags));
      setValue('isInternal', data.is_internal || false);
      setValue(
        'isShared',
        data.is_shared !== undefined ? data.is_shared : true,
      );

      if (data.input) {
        setValue('input', JSON.stringify(data.input, null, 2));
      }
    };

    const onSubmitForm = async (data: ImportTemplateFormData) => {
      if (!data.templateName || !data.templateVersion) {
        onError('Template name and version are required');
        return;
      }

      // Parse input JSON if provided
      let parsedInput: Record<string, any> | undefined;
      if (data.input && data.input.trim()) {
        try {
          parsedInput = JSON.parse(data.input);
        } catch (err) {
          onError('Invalid JSON in Input field');
          return;
        }
      }

      setLoading(true);
      try {
        // Convert form data to API request format
        const requestData: ImportTemplateRequest = {
          templateName: data.templateName,
          templateVersion: data.templateVersion,
          name: data.name || null,
          verboseName: data.verboseName || null,
          descriptionShort: data.descriptionShort || null,
          descriptionLong: data.descriptionLong || null,
          logo: data.logo || null,
          tags: parseTags(data.tags),
          isInternal: data.isInternal,
          isShared: data.isShared,
          input: parsedInput,
        };

        await onSubmit(requestData);
        // Don't reset here - let the parent component handle it
      } finally {
        setLoading(false);
      }
    };

    // When in modal, use the prop directly. Otherwise use the old logic
    const isReadOnly = isInModal
      ? isReadOnlyProp
      : editingTemplate && !isEditMode;

    return (
      <form
        ref={ref}
        onSubmit={handleFormSubmit(onSubmitForm)}
        className="launchpad-admin-form launchpad-admin-import-template-form space-y-6"
        data-section="import-template-form"
        data-form-mode={mode}
        data-read-only={isReadOnly ? 'true' : 'false'}
        data-record-id={editingTemplate?.id}
      >
        {/* Info Banner - Only show when not in modal */}
        {!isInModal && (
          <div
            className="launchpad-admin-form-banner launchpad-admin-template-form-banner rounded-lg bg-primary-subtle p-4"
            data-section="template-form-banner"
          >
            {editingTemplate ? (
              <div className="launchpad-admin-form-banner-content flex items-center justify-between">
                <p className="launchpad-admin-template-summary text-body text-neutral-700">
                  <strong>{isEditMode ? 'Editing' : 'Viewing'}:</strong>{' '}
                  {editingTemplate.verboseName} ({editingTemplate.templateName}{' '}
                  v{editingTemplate.templateVersion})
                </p>
                {!isEditMode && onCancel && (
                  <div className="launchpad-admin-form-banner-actions flex gap-2">
                    <Button
                      type="button"
                      onClick={() => setIsEditMode(true)}
                      variant="primary"
                      className="launchpad-admin-template-edit-button"
                      data-action="edit-template"
                    >
                      Edit
                    </Button>
                    <Button
                      type="button"
                      onClick={onCancel}
                      variant="secondary"
                      className="launchpad-admin-template-close-button"
                      data-action="close-template"
                    >
                      Close
                    </Button>
                  </div>
                )}
              </div>
            ) : (
              <p className="launchpad-admin-template-form-note text-body text-neutral-700">
                <strong>Note:</strong> Empty fields will be automatically filled
                with information from the Apolo Apps API when available.
              </p>
            )}
          </div>
        )}

        {/* Mode Toggle - Only show when not in read-only view and not editing in modal */}
        {!isReadOnly && !(isInModal && editingTemplate) && (
          <div
            className="launchpad-admin-form-mode-toggle flex gap-0 border-b border-neutral-300"
            data-section="template-input-mode"
          >
            <Button
              type="button"
              onClick={() => setMode('manual')}
              theme={false}
              stopPropagation={false}
              className={`launchpad-admin-form-mode-button relative cursor-pointer border-0 bg-transparent px-6 pb-3 pt-2 text-body font-medium transition-colors hover:bg-neutral-100 ${
                mode === 'manual'
                  ? 'text-primary after:absolute after:inset-x-0 after:bottom-0 after:h-0.5 after:bg-primary'
                  : 'text-neutral-600'
              }`}
              data-action="select-manual-entry"
              data-state={mode === 'manual' ? 'active' : 'inactive'}
            >
              Manual Entry
            </Button>
            <Button
              type="button"
              onClick={() => setMode('file')}
              theme={false}
              stopPropagation={false}
              className={`launchpad-admin-form-mode-button relative cursor-pointer border-0 bg-transparent px-6 pb-3 pt-2 text-body font-medium transition-colors hover:bg-neutral-100 ${
                mode === 'file'
                  ? 'text-primary after:absolute after:inset-x-0 after:bottom-0 after:h-0.5 after:bg-primary'
                  : 'text-neutral-600'
              }`}
              data-action="select-file-upload"
              data-state={mode === 'file' ? 'active' : 'inactive'}
            >
              Upload File
            </Button>
          </div>
        )}

        {/* File Upload Mode - Only show when not in read-only view and not editing in modal */}
        {!isReadOnly && !(isInModal && editingTemplate) && mode === 'file' && (
          <FileUpload onDataParsed={handleFileDataParsed} onError={onError} />
        )}

        {/* Form Fields */}
        <div
          className="launchpad-admin-form-fields grid grid-cols-2 gap-4 sm:grid-cols-1"
          data-section="form-fields"
        >
          <Field.Input
            variant="static"
            label="Template Name"
            required
            type="text"
            {...register('templateName')}
            className={cn(
              'launchpad-admin-form-control launchpad-admin-template-field-template-name',
              editingTemplate &&
                'cursor-not-allowed bg-neutral-100 text-neutral-600',
            )}
            containerClassName="launchpad-admin-form-field launchpad-admin-form-field-template-name"
            data-field-slot="template-name"
            readOnly={!!editingTemplate}
            disabled={!!editingTemplate}
            error={errors.templateName?.message}
            note={
              editingTemplate
                ? 'Template name cannot be changed when editing'
                : undefined
            }
          />

          <Field.Input
            variant="static"
            label="Template Version"
            required
            type="text"
            {...register('templateVersion')}
            className={cn(
              'launchpad-admin-form-control launchpad-admin-template-field-template-version',
              editingTemplate &&
                'cursor-not-allowed bg-neutral-100 text-neutral-600',
            )}
            containerClassName="launchpad-admin-form-field launchpad-admin-form-field-template-version"
            data-field-slot="template-version"
            readOnly={!!editingTemplate}
            disabled={!!editingTemplate}
            error={errors.templateVersion?.message}
            note={
              editingTemplate
                ? 'Template version cannot be changed when editing'
                : undefined
            }
          />

          <Field.Input
            variant="static"
            label="Internal Template Name"
            tooltip="This internal name is different from the Apolo Template Name and allows admins to import the same Apolo Template with different configurations (similar to importing multiple Service Deployments as custom apps to Launchpad)"
            type="text"
            {...register('name')}
            className={cn(
              'launchpad-admin-form-control launchpad-admin-template-field-name',
              (editingTemplate || isReadOnly) &&
                'cursor-not-allowed bg-neutral-100 text-neutral-600',
            )}
            containerClassName="launchpad-admin-form-field launchpad-admin-form-field-name"
            data-field-slot="name"
            readOnly={!!editingTemplate || isReadOnly || undefined}
            disabled={!!editingTemplate || undefined}
            error={errors.name?.message}
            note={
              editingTemplate
                ? 'Internal name cannot be changed when editing'
                : undefined
            }
          />

          <Field.Input
            variant="static"
            label="Display Name"
            tooltip="User-friendly name shown in the UI as the app name"
            type="text"
            {...register('verboseName')}
            className={cn(
              'launchpad-admin-form-control launchpad-admin-template-field-display-name',
              isReadOnly && 'bg-neutral-50 text-neutral-700',
            )}
            containerClassName="launchpad-admin-form-field launchpad-admin-form-field-display-name"
            data-field-slot="display-name"
            readOnly={isReadOnly || undefined}
            error={errors.verboseName?.message}
          />

          <div
            className="launchpad-admin-form-field launchpad-admin-form-field-logo col-span-2 sm:col-span-1"
            data-field-slot="logo"
          >
            <Field.Input
              variant="static"
              label="Logo URL"
              type="url"
              {...register('logo')}
              className={cn(
                'launchpad-admin-form-control launchpad-admin-template-field-logo',
                isReadOnly && 'bg-neutral-50 text-neutral-700',
              )}
              containerClassName="launchpad-admin-field-container"
              placeholder={isReadOnly ? '' : 'https://...'}
              readOnly={isReadOnly || undefined}
              error={errors.logo?.message}
            />
          </div>

          <div
            className="launchpad-admin-form-field launchpad-admin-form-field-short-description col-span-2 sm:col-span-1"
            data-field-slot="short-description"
          >
            <Field.Textarea
              variant="static"
              label="Short Description"
              {...register('descriptionShort')}
              rows={2}
              className={cn(
                'launchpad-admin-form-control launchpad-admin-template-field-short-description',
                isReadOnly && 'bg-neutral-50 text-neutral-700',
              )}
              containerClassName="launchpad-admin-field-container"
              readOnly={isReadOnly || undefined}
              error={errors.descriptionShort?.message}
            />
          </div>

          <div
            className="launchpad-admin-form-field launchpad-admin-form-field-long-description col-span-2 sm:col-span-1"
            data-field-slot="long-description"
          >
            <Field.Textarea
              variant="static"
              label="Long Description"
              {...register('descriptionLong')}
              rows={4}
              className={cn(
                'launchpad-admin-form-control launchpad-admin-template-field-long-description',
                isReadOnly && 'bg-neutral-50 text-neutral-700',
              )}
              containerClassName="launchpad-admin-field-container"
              readOnly={isReadOnly || undefined}
              error={errors.descriptionLong?.message}
            />
          </div>

          <div
            className="launchpad-admin-form-field launchpad-admin-form-field-tags col-span-2 sm:col-span-1"
            data-field-slot="tags"
          >
            <Field.Input
              variant="static"
              label="Tags (comma-separated)"
              type="text"
              {...register('tags')}
              className={cn(
                'launchpad-admin-form-control launchpad-admin-template-field-tags',
                isReadOnly && 'bg-neutral-50 text-neutral-700',
              )}
              containerClassName="launchpad-admin-field-container"
              placeholder={isReadOnly ? '' : 'tag1, tag2, tag3'}
              readOnly={isReadOnly || undefined}
              error={errors.tags?.message}
            />
          </div>

          <div
            className="launchpad-admin-form-field launchpad-admin-form-field-input col-span-2 sm:col-span-1"
            data-field-slot="input"
          >
            <Field.Textarea
              variant="static"
              label="Input (JSON)"
              {...register('input')}
              rows={6}
              className={cn(
                'launchpad-admin-form-control launchpad-admin-template-field-input font-mono text-caption',
                isReadOnly && 'bg-neutral-50 text-neutral-700',
              )}
              containerClassName="launchpad-admin-field-container"
              placeholder={
                isReadOnly
                  ? ''
                  : '{"preset": {"name": "cpu-small"}, "customKey": "value"}'
              }
              readOnly={isReadOnly ?? undefined}
              error={errors.input?.message}
              note="Optional: Provide default configuration values that will be merged with user inputs when installing this template."
            />
          </div>

          <div
            className="launchpad-admin-form-field launchpad-admin-form-field-flags col-span-2 sm:col-span-1"
            data-section="template-flags"
          >
            <div className="launchpad-admin-checkbox-group space-y-3">
              <label
                className={cn(
                  'launchpad-admin-checkbox-label flex items-start',
                  isReadOnly || templateHasInstances
                    ? 'cursor-not-allowed opacity-60'
                    : 'cursor-pointer',
                )}
                data-field-slot="internal"
              >
                <input
                  type="checkbox"
                  {...register('isInternal')}
                  disabled={isReadOnly || templateHasInstances}
                  className={cn(
                    'launchpad-admin-checkbox launchpad-admin-template-field-internal flex cursor-pointer items-start',
                    {
                      'cursor-not-allowed opacity-60': isReadOnly,
                    },
                  )}
                  data-action="toggle-internal"
                />
                <div className="launchpad-admin-checkbox-content">
                  <span className="launchpad-admin-checkbox-title text-body font-medium">
                    Internal
                  </span>
                  <p className="launchpad-admin-checkbox-description text-caption text-neutral-600">
                    Mark this template as internal (hidden from public app pool)
                  </p>
                  {templateHasInstances && !isReadOnly && (
                    <p className="launchpad-admin-field-warning mt-1 text-caption text-warning">
                      Cannot edit: This template has associated instances
                    </p>
                  )}
                </div>
              </label>

              <label
                className={cn(
                  'launchpad-admin-checkbox-label flex items-start',
                  isReadOnly || templateHasInstances
                    ? 'cursor-not-allowed opacity-60'
                    : 'cursor-pointer',
                )}
                data-field-slot="shared"
              >
                <input
                  type="checkbox"
                  {...register('isShared')}
                  className={cn(
                    'launchpad-admin-checkbox launchpad-admin-template-field-shared mr-3 mt-1',
                    (isReadOnly || templateHasInstances) &&
                      'cursor-not-allowed',
                  )}
                  disabled={isReadOnly || templateHasInstances}
                  data-action="toggle-shared"
                />
                <div className="launchpad-admin-checkbox-content">
                  <span className="launchpad-admin-checkbox-title text-body font-medium">
                    Shared
                  </span>
                  <p className="launchpad-admin-checkbox-description text-caption text-neutral-600">
                    <strong>Shared:</strong> A single instance is shared by all
                    users.
                    <br />
                    <strong>Not Shared:</strong> A new instance is installed for
                    each user that accesses it.
                  </p>
                  {templateHasInstances && !isReadOnly && (
                    <p className="launchpad-admin-field-warning mt-1 text-caption text-warning">
                      Cannot edit: This template has associated instances
                    </p>
                  )}
                </div>
              </label>
            </div>
          </div>
        </div>

        {/* Submit Button - Only show when not in read-only mode and not in modal */}
        {!isReadOnly && !isInModal && (
          <div
            className="launchpad-admin-form-actions flex justify-end gap-3"
            data-section="form-actions"
          >
            {editingTemplate && onCancel && (
              <Button
                type="button"
                onClick={onCancel}
                disabled={loading}
                className="launchpad-admin-form-cancel-button bg-neutral-200 text-neutral-700 hover:bg-neutral-300"
                data-action="cancel-template-form"
              >
                Cancel
              </Button>
            )}
            <Button
              type="submit"
              disabled={loading}
              className="launchpad-admin-form-submit-button"
              data-action={
                editingTemplate ? 'update-template' : 'import-template'
              }
            >
              {(() => {
                if (loading) {
                  return editingTemplate ? 'Updating...' : 'Importing...';
                }
                return editingTemplate ? 'Update Template' : 'Import Template';
              })()}
            </Button>
          </div>
        )}
      </form>
    );
  },
);

ImportTemplateForm.displayName = 'ImportTemplateForm';
