'use client';

import { useState } from 'react';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';

import { ImportAppRequest } from '@typings';
import { parseTags } from '@utils/helpers';

import { Button, Field } from '@components/Shared';

import { ImportAppFormData, importAppSchema } from './schemas';
import { UnimportedInstancesList } from './UnimportedInstancesList';

type ImportAppFormProps = {
  onSubmit: (data: ImportAppRequest) => Promise<void>;
  onError: (error: string) => void;
};

export const ImportAppForm: React.FC<ImportAppFormProps> = ({
  onSubmit,
  onError,
}) => {
  const [selectedInstance, setSelectedInstance] = useState<any | null>(null);
  const [loading, setLoading] = useState(false);

  const {
    register,
    handleSubmit: handleFormSubmit,
    formState: { errors },
    reset,
    setValue,
  } = useForm<ImportAppFormData>({
    resolver: zodResolver(importAppSchema),
    defaultValues: {
      appId: '',
      name: '',
      verboseName: '',
      descriptionShort: '',
      descriptionLong: '',
      logo: '',
      tags: '',
      isInternal: false,
    },
  });

  const handleSelectFromList = (instance: any) => {
    // Store the selected instance for display
    setSelectedInstance(instance);

    // Pre-fill the form with the selected instance data
    setValue('appId', instance.id || '');
    setValue('name', instance.name || '');
    setValue('verboseName', instance.displayName || '');
    setValue('descriptionShort', '');
    setValue('descriptionLong', '');
    setValue('logo', '');
    setValue('tags', '');
    // If the instance has no endpoints, it should be marked as internal
    setValue(
      'isInternal',
      !instance.endpoints || instance.endpoints.length === 0,
    );
  };

  const handleBackToList = () => {
    setSelectedInstance(null);
    reset();
  };

  const onSubmitForm = async (data: ImportAppFormData) => {
    setLoading(true);
    try {
      // Convert form data to API request format
      const requestData: ImportAppRequest = {
        appId: data.appId,
        name: data.name || null,
        verboseName: data.verboseName || null,
        descriptionShort: data.descriptionShort || null,
        descriptionLong: data.descriptionLong || null,
        logo: data.logo || null,
        tags: parseTags(data.tags),
        isInternal: data.isInternal,
      };

      await onSubmit(requestData);
      // Reset form and selection
      setSelectedInstance(null);
      reset();
    } catch (error: any) {
      onError(error.message || 'Failed to import app');
    } finally {
      setLoading(false);
    }
  };

  // If no instance selected, show the list
  if (!selectedInstance) {
    return (
      <UnimportedInstancesList
        onSelect={handleSelectFromList}
        onError={onError}
      />
    );
  }

  // If instance selected, show the form
  return (
    <form
      onSubmit={handleFormSubmit(onSubmitForm)}
      className="launchpad-admin-form launchpad-admin-import-app-form space-y-6"
      data-section="import-app-form"
      data-record-id={selectedInstance.id}
    >
      {/* Info Banner */}
      <div
        className="launchpad-admin-form-banner launchpad-admin-selected-app-banner rounded-lg bg-primary-subtle p-4"
        data-section="selected-app"
      >
        <div className="launchpad-admin-form-banner-content flex items-center justify-between">
          <p className="launchpad-admin-selected-app-summary text-body text-neutral-700">
            <strong>Selected App:</strong> {selectedInstance.displayName} (
            {selectedInstance.templateName} v{selectedInstance.templateVersion})
          </p>
          <Button
            type="button"
            onClick={handleBackToList}
            variant="secondary"
            className="launchpad-admin-back-to-app-list-button text-caption"
            data-action="back-to-app-list"
          >
            Back to List
          </Button>
        </div>
      </div>

      {/* Form Fields */}
      <div
        className="launchpad-admin-form-fields grid grid-cols-2 gap-4 sm:grid-cols-1"
        data-section="form-fields"
      >
        <div
          className="launchpad-admin-form-field launchpad-admin-form-field-app-id col-span-2 sm:col-span-1"
          data-field-slot="app-id"
        >
          <Field.Input
            variant="static"
            label="App ID (UUID)"
            required
            type="text"
            {...register('appId')}
            className="launchpad-admin-form-control launchpad-admin-app-field-app-id cursor-not-allowed bg-neutral-100 font-mono text-caption text-neutral-600"
            containerClassName="launchpad-admin-field-container"
            readOnly
            disabled
            error={errors.appId?.message}
            note="App ID is automatically set from the selected instance"
          />
        </div>

        <Field.Input
          variant="static"
          label="Internal Template Name"
          tooltip="Internal identifier used in the system"
          type="text"
          {...register('name')}
          className="launchpad-admin-form-control launchpad-admin-app-field-name"
          containerClassName="launchpad-admin-form-field launchpad-admin-form-field-name"
          data-field-slot="name"
          error={errors.name?.message}
        />

        <Field.Input
          variant="static"
          label="Display Name"
          tooltip="User-friendly name shown in the UI as the app name"
          type="text"
          {...register('verboseName')}
          className="launchpad-admin-form-control launchpad-admin-app-field-display-name"
          containerClassName="launchpad-admin-form-field launchpad-admin-form-field-display-name"
          data-field-slot="display-name"
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
            className="launchpad-admin-form-control launchpad-admin-app-field-logo"
            containerClassName="launchpad-admin-field-container"
            placeholder="https://..."
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
            className="launchpad-admin-form-control launchpad-admin-app-field-short-description"
            containerClassName="launchpad-admin-field-container"
            rows={2}
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
            className="launchpad-admin-form-control launchpad-admin-app-field-long-description"
            containerClassName="launchpad-admin-field-container"
            rows={4}
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
            className="launchpad-admin-form-control launchpad-admin-app-field-tags"
            containerClassName="launchpad-admin-field-container"
            placeholder="tag1, tag2, tag3"
            error={errors.tags?.message}
          />
        </div>

        <div
          className="launchpad-admin-form-field launchpad-admin-form-field-internal col-span-2 sm:col-span-1"
          data-field-slot="internal"
        >
          <label className="launchpad-admin-checkbox-label flex cursor-pointer items-start">
            <input
              type="checkbox"
              {...register('isInternal')}
              className="launchpad-admin-checkbox launchpad-admin-app-field-internal mr-3 mt-1"
              data-action="toggle-internal"
            />
            <div className="launchpad-admin-checkbox-content">
              <span className="launchpad-admin-checkbox-title text-body font-medium">
                Internal
              </span>
              <p className="launchpad-admin-checkbox-description text-caption text-neutral-600">
                This app will not appear in the app list to users. This is
                enabled automatically if the app does not expose a main public
                web page.
              </p>
            </div>
          </label>
        </div>
      </div>

      {/* Submit Button */}
      <div
        className="launchpad-admin-form-actions flex justify-end gap-3"
        data-section="form-actions"
      >
        <Button
          type="button"
          onClick={handleBackToList}
          disabled={loading}
          variant="secondary"
          className="launchpad-admin-form-cancel-button"
          data-action="cancel-import-app"
        >
          Cancel
        </Button>
        <Button
          type="submit"
          disabled={loading}
          className="launchpad-admin-form-submit-button"
          data-action="submit-import-app"
        >
          {loading ? 'Importing...' : 'Import App'}
        </Button>
      </div>
    </form>
  );
};
