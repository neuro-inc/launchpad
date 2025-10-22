'use client';

import { faTrash } from '@fortawesome/pro-regular-svg-icons';
import clsx from 'clsx';

import { InstalledApp } from '@typings';

import { Button, Icon, Table } from '@components/Shared';

type InstancesTableProps = {
  instances: InstalledApp[];
  onDelete?: (instance: InstalledApp) => void;
};

export const InstancesTable: React.FC<InstancesTableProps> = ({
  instances,
  onDelete,
}) => {
  if (instances.length === 0) {
    return (
      <div className="py-8 text-center text-neutral-500">
        No app instances found. Import apps to get started.
      </div>
    );
  }

  return (
    <div className="overflow-x-auto">
      <Table className="w-full grid-cols-[2fr_1.5fr_1.2fr_1fr_0.8fr_1fr_1.2fr]">
        <Table.Header>
          <Table.Row>
            <Table.Head className="border-b border-neutral-300 bg-neutral-100 text-h6">
              App Name
            </Table.Head>
            <Table.Head className="border-b border-neutral-300 bg-neutral-100 text-h6">
              Launchpad Name
            </Table.Head>
            <Table.Head className="border-b border-neutral-300 bg-neutral-100 text-h6">
              Template
            </Table.Head>
            <Table.Head className="border-b border-neutral-300 bg-neutral-100 text-h6">
              User ID
            </Table.Head>
            <Table.Head className="border-b border-neutral-300 bg-neutral-100 text-h6">
              URL
            </Table.Head>
            <Table.Head className="border-b border-neutral-300 bg-neutral-100 text-h6">
              Flags
            </Table.Head>
            <Table.Head className="border-b border-neutral-300 bg-neutral-100 text-h6">
              Actions
            </Table.Head>
          </Table.Row>
        </Table.Header>
        <Table.Body>
          {instances.map((instance, index) => {
            const isEven = index % 2 === 0;
            const cellBg = isEven ? 'bg-white' : 'bg-neutral-50';

            return (
              <Table.Row key={instance.id || `${instance.appId}-${index}`}>
                <Table.Cell
                  className={clsx('border-b border-neutral-200', cellBg)}
                >
                  <div className="text-body font-medium">
                    {instance.appName}
                  </div>
                  <div className="text-caption text-neutral-500">
                    ID: {instance.appId}
                  </div>
                </Table.Cell>
                <Table.Cell
                  className={clsx('border-b border-neutral-200', cellBg)}
                >
                  <div className="text-body">{instance.launchpadAppName}</div>
                </Table.Cell>
                <Table.Cell
                  className={clsx('border-b border-neutral-200', cellBg)}
                >
                  <div className="text-body">{instance.templateName}</div>
                </Table.Cell>
                <Table.Cell
                  className={clsx('border-b border-neutral-200', cellBg)}
                >
                  <div className="text-body text-neutral-700">
                    {instance.userId || '-'}
                  </div>
                </Table.Cell>
                <Table.Cell
                  className={clsx('border-b border-neutral-200', cellBg)}
                >
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
                    <span className="text-caption text-neutral-500">-</span>
                  )}
                </Table.Cell>
                <Table.Cell
                  className={clsx('border-b border-neutral-200', cellBg)}
                >
                  <div className="flex flex-col gap-1">
                    {instance.isInternal && (
                      <span className="rounded bg-neutral-200 px-2 py-1 text-caption text-neutral-700">
                        Internal
                      </span>
                    )}
                    {instance.isShared && (
                      <span className="rounded bg-success px-2 py-1 text-caption text-white">
                        Shared
                      </span>
                    )}
                  </div>
                </Table.Cell>
                <Table.Cell
                  className={clsx('border-b border-neutral-200', cellBg)}
                >
                  <Button
                    variant="ghost"
                    onClick={() => onDelete?.(instance)}
                    className="px-2 py-1 text-caption text-error hover:bg-error-subtle"
                    title="Delete instance"
                  >
                    <Icon icon={faTrash} className="mr-1" />
                    Delete
                  </Button>
                </Table.Cell>
              </Table.Row>
            );
          })}
        </Table.Body>
      </Table>
    </div>
  );
};
