'use client';

import { DragEvent, useRef, useState } from 'react';
import yaml from 'js-yaml';
import {
  faCircleCheck,
  faCloudArrowUp,
  faXmark,
} from '@fortawesome/pro-regular-svg-icons';
import clsx from 'clsx';

import { Button, Icon } from '@components/Shared';

type FileUploadProps = {
  onDataParsed: (data: any) => void;
  onError: (error: string) => void;
  acceptedFormats?: string[];
  maxSizeMB?: number;
};

export const FileUpload: React.FC<FileUploadProps> = ({
  onDataParsed,
  onError,
  acceptedFormats = ['.json', '.yaml', '.yml'],
  maxSizeMB = 1,
}) => {
  const [isDragging, setIsDragging] = useState(false);
  const [fileName, setFileName] = useState<string | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const parseFile = async (file: File) => {
    // Check file size
    const maxSizeBytes = maxSizeMB * 1024 * 1024;
    if (file.size > maxSizeBytes) {
      onError(`File size exceeds ${maxSizeMB}MB limit`);
      return;
    }

    // Read file content
    const text = await file.text();

    try {
      let data: any;

      // Try parsing as JSON first
      if (file.name.endsWith('.json')) {
        data = JSON.parse(text);
      } else if (file.name.endsWith('.yaml') || file.name.endsWith('.yml')) {
        data = yaml.load(text);
      } else {
        // Try JSON first, then YAML
        try {
          data = JSON.parse(text);
        } catch {
          data = yaml.load(text);
        }
      }

      setFileName(file.name);
      onDataParsed(data);
    } catch (error: any) {
      onError(`Failed to parse file: ${error.message}`);
      setFileName(null);
    }
  };

  const handleDragEnter = (e: DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragging(true);
  };

  const handleDragLeave = (e: DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragging(false);
  };

  const handleDragOver = (e: DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    e.stopPropagation();
  };

  const handleDrop = (e: DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragging(false);

    const { files } = e.dataTransfer;
    if (files && files.length > 0) {
      parseFile(files[0]);
    }
  };

  const handleFileSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
    const { files } = e.target;
    if (files && files.length > 0) {
      parseFile(files[0]);
    }
  };

  const handleClear = () => {
    setFileName(null);
    if (fileInputRef.current) {
      fileInputRef.current.value = '';
    }
  };

  return (
    <div
      className="launchpad-admin-file-upload space-y-4"
      data-section="file-upload"
      data-state={fileName ? 'selected' : 'empty'}
    >
      <div
        role="button"
        tabIndex={0}
        onDragEnter={handleDragEnter}
        onDragOver={handleDragOver}
        onDragLeave={handleDragLeave}
        onDrop={handleDrop}
        onClick={() => fileInputRef.current?.click()}
        onKeyDown={(e) => {
          if (e.key === 'Enter' || e.key === ' ') {
            e.preventDefault();
            fileInputRef.current?.click();
          }
        }}
        className={clsx(
          'launchpad-admin-file-dropzone rounded-lg border-2 border-dashed p-8',
          'flex flex-col items-center justify-center',
          'cursor-pointer transition-colors',
          isDragging
            ? 'border-primary bg-primary-light'
            : 'border-neutral-300 hover:border-primary-medium hover:bg-neutral-50',
        )}
        data-action="select-file"
        data-state={isDragging ? 'dragging' : 'idle'}
      >
        <Icon
          icon={faCloudArrowUp}
          className="launchpad-admin-file-upload-icon mb-4 text-neutral-400"
          size="3x"
        />
        <p className="launchpad-admin-file-upload-prompt mb-2 text-body text-neutral-700">
          Drag and drop a file here, or click to browse
        </p>
        <p className="launchpad-admin-file-upload-help text-caption text-neutral-500">
          Accepts: {acceptedFormats.join(', ')} (max {maxSizeMB}MB)
        </p>
        <input
          ref={fileInputRef}
          type="file"
          accept={acceptedFormats.join(',')}
          onChange={handleFileSelect}
          className="launchpad-admin-file-input hidden"
          data-action="upload-file"
        />
      </div>

      {fileName && (
        <div
          className="launchpad-admin-selected-file flex items-center justify-between rounded-lg bg-neutral-100 p-3"
          data-section="selected-file"
          data-file-name={fileName}
        >
          <div className="launchpad-admin-selected-file-details flex items-center">
            <Icon
              icon={faCircleCheck}
              className="launchpad-admin-selected-file-icon mr-2 text-primary"
            />
            <span className="launchpad-admin-selected-file-name text-body text-neutral-700">
              {fileName}
            </span>
          </div>
          <Button
            type="button"
            onClick={handleClear}
            theme={false}
            variant="ghost"
            className="launchpad-admin-clear-file-button text-neutral-500 hover:text-neutral-700"
            data-action="clear-file"
            aria-label="Clear file"
            icon={faXmark}
          />
        </div>
      )}
    </div>
  );
};
