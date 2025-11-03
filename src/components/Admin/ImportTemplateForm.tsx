'use client';

import { forwardRef, useEffect, useMemo, useState } from 'react';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';

import { ImportTemplateRequest, InstalledApp, Template } from '@typings';
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
        className="space-y-6"
      >
        {/* Info Banner - Only show when not in modal */}
        {!isInModal && (
          <div className="rounded-lg bg-primary-subtle p-4">
            {editingTemplate ? (
              <div className="flex items-center justify-between">
                <p className="text-body text-neutral-700">
                  <strong>{isEditMode ? 'Editing' : 'Viewing'}:</strong>{' '}
                  {editingTemplate.verboseName} ({editingTemplate.templateName}{' '}
                  v{editingTemplate.templateVersion})
                </p>
                {!isEditMode && onCancel && (
                  <div className="flex gap-2">
                    <Button
                      type="button"
                      onClick={() => setIsEditMode(true)}
                      variant="primary"
                    >
                      Edit
                    </Button>
                    <Button
                      type="button"
                      onClick={onCancel}
                      variant="secondary"
                    >
                      Close
                    </Button>
                  </div>
                )}
              </div>
            ) : (
              <p className="text-body text-neutral-700">
                <strong>Note:</strong> Empty fields will be automatically filled
                with information from the Apolo Apps API when available.
              </p>
            )}
          </div>
        )}

        {/* Mode Toggle - Only show when not in read-only view and not editing in modal */}
        {!isReadOnly && !(isInModal && editingTemplate) && (
          <div className="flex gap-0 border-b border-neutral-300">
            <Button
              type="button"
              onClick={() => setMode('manual')}
              theme={false}
              stopPropagation={false}
              className={`relative cursor-pointer border-0 bg-transparent px-6 pb-3 pt-2 text-body font-medium transition-colors hover:bg-neutral-100 ${
                mode === 'manual'
                  ? 'text-primary after:absolute after:inset-x-0 after:bottom-0 after:h-0.5 after:bg-primary'
                  : 'text-neutral-600'
              }`}
            >
              Manual Entry
            </Button>
            <Button
              type="button"
              onClick={() => setMode('file')}
              theme={false}
              stopPropagation={false}
              className={`relative cursor-pointer border-0 bg-transparent px-6 pb-3 pt-2 text-body font-medium transition-colors hover:bg-neutral-100 ${
                mode === 'file'
                  ? 'text-primary after:absolute after:inset-x-0 after:bottom-0 after:h-0.5 after:bg-primary'
                  : 'text-neutral-600'
              }`}
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
        <div className="grid grid-cols-2 gap-4 sm:grid-cols-1">
          <Field.Input
            variant="static"
            label="Template Name"
            required
            type="text"
            {...register('templateName')}
            className={
              editingTemplate
                ? 'cursor-not-allowed bg-neutral-100 text-neutral-600'
                : ''
            }
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
            className={
              editingTemplate
                ? 'cursor-not-allowed bg-neutral-100 text-neutral-600'
                : ''
            }
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
            className={
              editingTemplate || isReadOnly
                ? 'cursor-not-allowed bg-neutral-100 text-neutral-600'
                : ''
            }
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
            className={isReadOnly ? 'bg-neutral-50 text-neutral-700' : ''}
            readOnly={isReadOnly || undefined}
            error={errors.verboseName?.message}
          />

          <div className="col-span-2 sm:col-span-1">
            <Field.Input
              variant="static"
              label="Logo URL"
              type="url"
              {...register('logo')}
              className={isReadOnly ? 'bg-neutral-50 text-neutral-700' : ''}
              placeholder={isReadOnly ? '' : 'https://...'}
              readOnly={isReadOnly || undefined}
              error={errors.logo?.message}
            />
          </div>

          <div className="col-span-2 sm:col-span-1">
            <Field.Textarea
              variant="static"
              label="Short Description"
              {...register('descriptionShort')}
              rows={2}
              className={isReadOnly ? 'bg-neutral-50 text-neutral-700' : ''}
              readOnly={isReadOnly || undefined}
              error={errors.descriptionShort?.message}
            />
          </div>

          <div className="col-span-2 sm:col-span-1">
            <Field.Textarea
              variant="static"
              label="Long Description"
              {...register('descriptionLong')}
              rows={4}
              className={isReadOnly ? 'bg-neutral-50 text-neutral-700' : ''}
              readOnly={isReadOnly || undefined}
              error={errors.descriptionLong?.message}
            />
          </div>

          <div className="col-span-2 sm:col-span-1">
            <Field.Input
              variant="static"
              label="Tags (comma-separated)"
              type="text"
              {...register('tags')}
              className={isReadOnly ? 'bg-neutral-50 text-neutral-700' : ''}
              placeholder={isReadOnly ? '' : 'tag1, tag2, tag3'}
              readOnly={isReadOnly || undefined}
              error={errors.tags?.message}
            />
          </div>

          <div className="col-span-2 sm:col-span-1">
            <Field.Textarea
              variant="static"
              label="Input (JSON)"
              {...register('input')}
              rows={6}
              className={
                isReadOnly
                  ? 'bg-neutral-50 font-mono text-caption text-neutral-700'
                  : 'font-mono text-caption'
              }
              placeholder={
                isReadOnly
                  ? ''
                  : '{"preset": {"name": "cpu-small"}, "customKey": "value"}'
              }
              readOnly={isReadOnly || undefined}
              error={errors.input?.message}
              note="Optional: Provide default configuration values that will be merged with user inputs when installing this template."
            />
          </div>

          <div className="col-span-2 sm:col-span-1">
            <div className="space-y-3">
              <label
                className={`flex items-start ${isReadOnly || templateHasInstances ? 'cursor-not-allowed opacity-60' : 'cursor-pointer'}`}
              >
                <input
                  type="checkbox"
                  {...register('isInternal')}
                  className={`mr-3 mt-1 ${isReadOnly || templateHasInstances ? 'cursor-not-allowed' : ''}`}
                  disabled={isReadOnly || templateHasInstances}
                />
                <div>
                  <span className="text-body font-medium">Internal</span>
                  <p className="text-caption text-neutral-600">
                    Mark this template as internal (hidden from public app pool)
                  </p>
                  {templateHasInstances && !isReadOnly && (
                    <p className="mt-1 text-caption text-warning">
                      Cannot edit: This template has associated instances
                    </p>
                  )}
                </div>
              </label>

              <label
                className={`flex items-start ${isReadOnly || templateHasInstances ? 'cursor-not-allowed opacity-60' : 'cursor-pointer'}`}
              >
                <input
                  type="checkbox"
                  {...register('isShared')}
                  className={`mr-3 mt-1 ${isReadOnly || templateHasInstances ? 'cursor-not-allowed' : ''}`}
                  disabled={isReadOnly || templateHasInstances}
                />
                <div>
                  <span className="text-body font-medium">Shared</span>
                  <p className="text-caption text-neutral-600">
                    <strong>Shared:</strong> A single instance is shared by all
                    users.
                    <br />
                    <strong>Not Shared:</strong> A new instance is installed for
                    each user that accesses it.
                  </p>
                  {templateHasInstances && !isReadOnly && (
                    <p className="mt-1 text-caption text-warning">
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
          <div className="flex justify-end gap-3">
            {editingTemplate && onCancel && (
              <Button
                type="button"
                onClick={onCancel}
                disabled={loading}
                className="bg-neutral-200 text-neutral-700 hover:bg-neutral-300"
              >
                Cancel
              </Button>
            )}
            <Button type="submit" disabled={loading}>
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
