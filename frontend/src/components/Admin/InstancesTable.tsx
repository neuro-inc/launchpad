'use client';

import {
  faArrowUpRightFromSquare,
  faCubesStacked,
  faTrash,
} from '@fortawesome/pro-regular-svg-icons';
import clsx from 'clsx';

import { InstalledApp } from '@typings';

import { Button, ChaseSpinner, Icon, Table } from '@components/Shared';

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
  isLoading?: boolean;
  onDelete?: (instance: InstalledApp) => void;
  rowBgColor?: string;
  rowAltBgColor?: string;
  headerBgColor?: string;
};

export const InstancesTable: React.FC<InstancesTableProps> = ({
  instances,
  isLoading = false,
  onDelete,
  rowBgColor,
  rowAltBgColor,
  headerBgColor,
}) => {
  const headerStyle = getSurfaceStyle(headerBgColor || '#f5f5f5');

  if (!isLoading && instances.length === 0) {
    return (
      <div
        className="launchpad-admin-empty-state launchpad-admin-instances-empty flex min-h-40 flex-col items-center justify-center px-6 py-10 text-center"
        data-section="instances-empty-state"
        data-state="empty"
      >
        <div className="mb-4 flex size-14 items-center justify-center rounded-2xl bg-secondary-subtle text-secondary-dark">
          <Icon icon={faCubesStacked} size="lg" />
        </div>
        <h3 className="text-h6 font-600 text-rebecca">No app instances yet</h3>
        <p className="mt-1 max-w-md text-body-medium text-neural-04">
          Import an existing application instance to manage it from this
          workspace.
        </p>
      </div>
    );
  }

  return (
    <div
      className="launchpad-admin-table-wrapper launchpad-admin-instances-table-wrapper min-h-28 overflow-x-auto"
      data-section="instances-table"
      data-state={isLoading ? 'loading' : 'loaded'}
    >
      <Table
        className="launchpad-admin-table launchpad-admin-instances-table min-w-[1080px] grid-cols-[2fr_1.5fr_1.2fr_1fr_0.8fr_1fr_1fr] rounded-none bg-transparent"
        aria-busy={isLoading}
      >
        <Table.Header className="launchpad-admin-table-header">
          <Table.Row className="launchpad-admin-table-header-row">
            {tableHeaders.map((header) => (
              <Table.Head
                key={header.key}
                className={clsx(
                  'launchpad-admin-table-header-cell launchpad-admin-instances-table-header-cell launchpad-admin-surface',
                  `launchpad-admin-column-${header.key}`,
                  'border-b border-neural-02 bg-neural-01 py-3 text-caption font-600 uppercase tracking-[0.08em] text-neural-04',
                )}
                style={headerStyle}
                data-column={header.key}
              >
                {header.label}
              </Table.Head>
            ))}
          </Table.Row>
        </Table.Header>

        {!isLoading && (
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
                  className="launchpad-admin-table-row launchpad-admin-instance-row group contents"
                  data-record-id={recordId}
                  data-record-name={
                    instance.launchpadAppName || instance.appName
                  }
                  data-record-type="instance"
                  data-row-variant={isEven ? 'primary' : 'alternate'}
                >
                  <Table.Cell
                    className={clsx(
                      'launchpad-admin-table-cell launchpad-admin-instance-cell launchpad-admin-instance-cell-app-name launchpad-admin-surface border-b border-neural-02 transition-[filter] group-hover:brightness-[0.985]',
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
                      'launchpad-admin-table-cell launchpad-admin-instance-cell launchpad-admin-instance-cell-launchpad-name launchpad-admin-surface border-b border-neural-02 transition-[filter] group-hover:brightness-[0.985]',
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
                      'launchpad-admin-table-cell launchpad-admin-instance-cell launchpad-admin-instance-cell-template launchpad-admin-surface border-b border-neural-02 transition-[filter] group-hover:brightness-[0.985]',
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
                      'launchpad-admin-table-cell launchpad-admin-instance-cell launchpad-admin-instance-cell-user-id launchpad-admin-surface border-b border-neural-02 transition-[filter] group-hover:brightness-[0.985]',
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
                      'launchpad-admin-table-cell launchpad-admin-instance-cell launchpad-admin-instance-cell-url launchpad-admin-surface border-b border-neural-02 transition-[filter] group-hover:brightness-[0.985]',
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
                          className="launchpad-admin-instance-link inline-flex items-center gap-1.5 text-body-medium font-600 text-primary hover:text-primary-dark"
                          data-action="open-instance"
                          data-record-id={recordId}
                        >
                          Open
                          <Icon
                            icon={faArrowUpRightFromSquare}
                            className="size-4"
                          />
                        </a>
                      ) : (
                        <span className="text-caption text-neutral-500">-</span>
                      )}
                    </div>
                  </Table.Cell>
                  <Table.Cell
                    className={clsx(
                      'launchpad-admin-table-cell launchpad-admin-instance-cell launchpad-admin-instance-cell-flags launchpad-admin-surface border-b border-neural-02 transition-[filter] group-hover:brightness-[0.985]',
                      cellBg,
                    )}
                    style={rowStyle}
                    data-column="flags"
                  >
                    <div className="launchpad-admin-cell-content launchpad-admin-instance-flags flex flex-col items-start gap-1">
                      {instance.isInternal && (
                        <span
                          className="launchpad-admin-record-flag rounded-full bg-neural-01 px-2.5 py-1 text-caption font-500 text-neural-05"
                          data-flag="internal"
                        >
                          Internal
                        </span>
                      )}
                      {instance.isShared && (
                        <span
                          className="launchpad-admin-record-flag rounded-full bg-success-subtle px-2.5 py-1 text-caption font-500 text-success-dark"
                          data-flag="shared"
                        >
                          Shared
                        </span>
                      )}
                    </div>
                  </Table.Cell>
                  <Table.Cell
                    className={clsx(
                      'launchpad-admin-table-cell launchpad-admin-instance-cell launchpad-admin-instance-cell-actions launchpad-admin-surface border-b border-neural-02 transition-[filter] group-hover:brightness-[0.985]',
                      cellBg,
                    )}
                    style={rowStyle}
                    data-column="actions"
                  >
                    <div className="launchpad-admin-cell-content launchpad-admin-record-actions">
                      <Button
                        variant="ghost"
                        onClick={() => onDelete?.(instance)}
                        className="launchpad-admin-record-action h-9 justify-start gap-1.5 rounded-lg px-2.5 py-1 text-body-small font-600 text-error hover:bg-error-subtle"
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
        )}
      </Table>
      {isLoading && (
        <div
          className="launchpad-admin-table-loading flex min-h-48 items-center justify-center gap-3 bg-white text-neural-04"
          data-section="instances-loading-state"
          data-state="loading"
        >
          <ChaseSpinner
            color="primary"
            className="launchpad-admin-loading-spinner size-5"
          />
          <span className="text-body-medium">Loading instances...</span>
        </div>
      )}
    </div>
  );
};
