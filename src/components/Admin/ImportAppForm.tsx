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
    <form onSubmit={handleFormSubmit(onSubmitForm)} className="space-y-6">
      {/* Info Banner */}
      <div className="rounded-lg bg-primary-subtle p-4">
        <div className="flex items-center justify-between">
          <p className="text-body text-neutral-700">
            <strong>Selected App:</strong> {selectedInstance.displayName} (
            {selectedInstance.templateName} v{selectedInstance.templateVersion})
          </p>
          <Button
            type="button"
            onClick={handleBackToList}
            variant="secondary"
            className="text-caption"
          >
            Back to List
          </Button>
        </div>
      </div>

      {/* Form Fields */}
      <div className="grid grid-cols-2 gap-4 sm:grid-cols-1">
        <div className="col-span-2 sm:col-span-1">
          <Field.Input
            variant="static"
            label="App ID (UUID)"
            required
            type="text"
            {...register('appId')}
            className="cursor-not-allowed bg-neutral-100 font-mono text-caption text-neutral-600"
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
          error={errors.name?.message}
        />

        <Field.Input
          variant="static"
          label="Display Name"
          tooltip="User-friendly name shown in the UI as the app name"
          type="text"
          {...register('verboseName')}
          error={errors.verboseName?.message}
        />

        <div className="col-span-2 sm:col-span-1">
          <Field.Input
            variant="static"
            label="Logo URL"
            type="url"
            {...register('logo')}
            placeholder="https://..."
            error={errors.logo?.message}
          />
        </div>

        <div className="col-span-2 sm:col-span-1">
          <Field.Textarea
            variant="static"
            label="Short Description"
            {...register('descriptionShort')}
            rows={2}
            error={errors.descriptionShort?.message}
          />
        </div>

        <div className="col-span-2 sm:col-span-1">
          <Field.Textarea
            variant="static"
            label="Long Description"
            {...register('descriptionLong')}
            rows={4}
            error={errors.descriptionLong?.message}
          />
        </div>

        <div className="col-span-2 sm:col-span-1">
          <Field.Input
            variant="static"
            label="Tags (comma-separated)"
            type="text"
            {...register('tags')}
            placeholder="tag1, tag2, tag3"
            error={errors.tags?.message}
          />
        </div>

        <div className="flex items-center gap-4">
          <Field.Checkbox label="Internal" {...register('isInternal')} />
        </div>
      </div>

      {/* Submit Button */}
      <div className="flex justify-end gap-3">
        <Button
          type="button"
          onClick={handleBackToList}
          disabled={loading}
          variant="secondary"
        >
          Cancel
        </Button>
        <Button type="submit" disabled={loading}>
          {loading ? 'Importing...' : 'Import App'}
        </Button>
      </div>
    </form>
  );
};
