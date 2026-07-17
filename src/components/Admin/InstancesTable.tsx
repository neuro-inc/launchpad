'use client';

import { faTrash } from '@fortawesome/pro-regular-svg-icons';
import clsx from 'clsx';

import { InstalledApp } from '@typings';

import { Button, Icon, Table } from '@components/Shared';

const tableHeaders = [
  { key: 'app-name', label: 'App Name' },
  { key: 'launchpad-name', label: 'Launchpad Name' },
  { key: 'template', label: 'Template' },
  { key: 'user-id', label: 'User ID' },
  { key: 'url', label: 'URL' },
  { key: 'flags', label: 'Flags' },
  { key: 'actions', label: 'Actions' },
] as const;

type AdminSurfaceStyle = React.CSSProperties & {
  '--launchpad-admin-surface-background'?: string;
};

const getSurfaceStyle = (color: string): AdminSurfaceStyle => ({
  '--launchpad-admin-surface-background': color,
});

type InstancesTableProps = {
  instances: InstalledApp[];
  onDelete?: (instance: InstalledApp) => void;
  rowBgColor?: string;
  rowAltBgColor?: string;
  headerBgColor?: string;
};

export const InstancesTable: React.FC<InstancesTableProps> = ({
  instances,
  onDelete,
  rowBgColor,
  rowAltBgColor,
  headerBgColor,
}) => {
  const headerStyle = getSurfaceStyle(headerBgColor || '#f5f5f5');

  if (instances.length === 0) {
    return (
      <div
        className="launchpad-admin-empty-state launchpad-admin-instances-empty py-8 text-center text-neutral-500"
        data-section="instances-empty-state"
        data-state="empty"
      >
        No app instances found. Import apps to get started.
      </div>
    );
  }

  return (
    <div
      className="launchpad-admin-table-wrapper launchpad-admin-instances-table-wrapper overflow-x-auto"
      data-section="instances-table"
    >
      <Table className="launchpad-admin-table launchpad-admin-instances-table w-full grid-cols-[2fr_1.5fr_1.2fr_1fr_0.8fr_1fr_1.2fr]">
        <Table.Header className="launchpad-admin-table-header">
          <Table.Row className="launchpad-admin-table-header-row">
            {tableHeaders.map((header) => (
              <Table.Head
                key={header.key}
                className={clsx(
                  'launchpad-admin-table-header-cell launchpad-admin-instances-table-header-cell launchpad-admin-surface',
                  `launchpad-admin-column-${header.key}`,
                  'border-b border-neutral-300 bg-neutral-100 text-h6',
                )}
                style={headerStyle}
                data-column={header.key}
              >
                {header.label}
              </Table.Head>
            ))}
          </Table.Row>
        </Table.Header>

        <Table.Body className="launchpad-admin-table-body launchpad-admin-instances-table-body">
          {instances.map((instance, index) => {
            const isEven = index % 2 === 0;
            const cellBg = isEven ? 'bg-white' : 'bg-neutral-50';
            const rowBackgroundColor = isEven
              ? rowBgColor || '#ffffff'
              : rowAltBgColor || '#fafafa';
            const rowStyle = getSurfaceStyle(rowBackgroundColor);
            const recordId = instance.id || instance.appId || index;

            return (
              <Table.Row
                key={instance.id || `${instance.appId}-${index}`}
                className="launchpad-admin-table-row launchpad-admin-instance-row contents"
                data-record-id={recordId}
                data-record-name={instance.launchpadAppName || instance.appName}
                data-record-type="instance"
                data-row-variant={isEven ? 'primary' : 'alternate'}
              >
                <Table.Cell
                  className={clsx(
                    'launchpad-admin-table-cell launchpad-admin-instance-cell launchpad-admin-instance-cell-app-name launchpad-admin-surface border-b border-neutral-200',
                    cellBg,
                  )}
                  style={rowStyle}
                  data-column="app-name"
                >
                  <div className="launchpad-admin-cell-content">
                    <div className="launchpad-admin-instance-app-name text-body font-medium">
                      {instance.appName}
                    </div>
                    <div className="launchpad-admin-instance-app-id text-caption text-neutral-500">
                      ID: {instance.appId}
                    </div>
                  </div>
                </Table.Cell>
                <Table.Cell
                  className={clsx(
                    'launchpad-admin-table-cell launchpad-admin-instance-cell launchpad-admin-instance-cell-launchpad-name launchpad-admin-surface border-b border-neutral-200',
                    cellBg,
                  )}
                  style={rowStyle}
                  data-column="launchpad-name"
                >
                  <div className="launchpad-admin-cell-content launchpad-admin-instance-launchpad-name text-body">
                    {instance.launchpadAppName}
                  </div>
                </Table.Cell>
                <Table.Cell
                  className={clsx(
                    'launchpad-admin-table-cell launchpad-admin-instance-cell launchpad-admin-instance-cell-template launchpad-admin-surface border-b border-neutral-200',
                    cellBg,
                  )}
                  style={rowStyle}
                  data-column="template"
                >
                  <div className="launchpad-admin-cell-content launchpad-admin-instance-template-name text-body">
                    {instance.templateName}
                  </div>
                </Table.Cell>
                <Table.Cell
                  className={clsx(
                    'launchpad-admin-table-cell launchpad-admin-instance-cell launchpad-admin-instance-cell-user-id launchpad-admin-surface border-b border-neutral-200',
                    cellBg,
                  )}
                  style={rowStyle}
                  data-column="user-id"
                >
                  <div className="launchpad-admin-cell-content launchpad-admin-instance-user-id text-body text-neutral-700">
                    {instance.userId || '-'}
                  </div>
                </Table.Cell>
                <Table.Cell
                  className={clsx(
                    'launchpad-admin-table-cell launchpad-admin-instance-cell launchpad-admin-instance-cell-url launchpad-admin-surface border-b border-neutral-200',
                    cellBg,
                  )}
                  style={rowStyle}
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
                      <span className="text-caption text-neutral-500">-</span>
                    )}
                  </div>
                </Table.Cell>
                <Table.Cell
                  className={clsx(
                    'launchpad-admin-table-cell launchpad-admin-instance-cell launchpad-admin-instance-cell-flags launchpad-admin-surface border-b border-neutral-200',
                    cellBg,
                  )}
                  style={rowStyle}
                  data-column="flags"
                >
                  <div className="launchpad-admin-cell-content launchpad-admin-instance-flags flex flex-col gap-1">
                    {instance.isInternal && (
                      <span
                        className="launchpad-admin-record-flag rounded bg-neutral-200 px-2 py-1 text-caption text-neutral-700"
                        data-flag="internal"
                      >
                        Internal
                      </span>
                    )}
                    {instance.isShared && (
                      <span
                        className="launchpad-admin-record-flag rounded bg-success px-2 py-1 text-caption text-white"
                        data-flag="shared"
                      >
                        Shared
                      </span>
                    )}
                  </div>
                </Table.Cell>
                <Table.Cell
                  className={clsx(
                    'launchpad-admin-table-cell launchpad-admin-instance-cell launchpad-admin-instance-cell-actions launchpad-admin-surface border-b border-neutral-200',
                    cellBg,
                  )}
                  style={rowStyle}
                  data-column="actions"
                >
                  <div className="launchpad-admin-cell-content launchpad-admin-record-actions">
                    <Button
                      variant="ghost"
                      onClick={() => onDelete?.(instance)}
                      className="launchpad-admin-record-action h-auto justify-start gap-1 px-0 py-1 text-caption text-error hover:bg-error-subtle"
                      data-action="delete-instance"
                      data-record-id={recordId}
                      title="Delete instance"
                    >
                      <Icon size="lg" icon={faTrash} />
                      Delete
                    </Button>
                  </div>
                </Table.Cell>
              </Table.Row>
            );
          })}
        </Table.Body>
      </Table>
    </div>
  );
};
