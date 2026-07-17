'use client';

import { useEffect, useState } from 'react';
import clsx from 'clsx';

import { UnimportedInstance } from '@typings';
import { formatToCamelCase } from '@utils/formatters';
import { clientRequest } from '@utils/helpers';

import { Button, Table } from '@components/Shared';

type UnimportedInstancesListProps = {
  onSelect: (instance: UnimportedInstance) => void;
  onError: (error: string) => void;
};

export const UnimportedInstancesList: React.FC<
  UnimportedInstancesListProps
> = ({ onSelect, onError }) => {
  const [instances, setInstances] = useState<UnimportedInstance[]>([]);
  const [loading, setLoading] = useState(true);

  const fetchUnimportedInstances = async () => {
    try {
      setLoading(true);
      const data = await clientRequest<{
        items: any[];
        total: number;
        page: number;
        size: number;
        pages: number;
      }>('/api/v1/apps/instances/unimported', {
        method: 'GET',
      });
      // Transform snake_case API response to camelCase
      const items = formatToCamelCase(data.items) as UnimportedInstance[];

      setInstances(items);
    } catch (error: any) {
      onError(error.message || 'Failed to fetch unimported instances');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchUnimportedInstances();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const handleSelect = (instance: UnimportedInstance) => {
    onSelect(instance);
  };

  if (loading) {
    return (
      <div
        className="launchpad-admin-loading-state launchpad-admin-unimported-instances-loading py-8 text-center text-neutral-500"
        data-section="unimported-instances"
        data-state="loading"
      >
        Loading running apps...
      </div>
    );
  }

  if (instances.length === 0) {
    return (
      <div
        className="launchpad-admin-empty-state launchpad-admin-unimported-instances-empty py-8 text-center text-neutral-500"
        data-section="unimported-instances"
        data-state="empty"
      >
        No running apps found to import.
      </div>
    );
  }

  return (
    <div
      className="launchpad-admin-unimported-instances space-y-4"
      data-section="unimported-instances"
      data-state="loaded"
    >
      <div className="launchpad-admin-unimported-instances-header flex items-center justify-between">
        <p className="launchpad-admin-unimported-instances-summary text-body text-neutral-700">
          Found {instances.length} running app
          {instances.length !== 1 ? 's' : ''}
        </p>
        <Button
          type="button"
          onClick={fetchUnimportedInstances}
          theme={false}
          variant="ghost-primary"
          className="launchpad-admin-unimported-instances-refresh text-body"
          data-action="refresh-unimported-instances"
        >
          Refresh
        </Button>
      </div>

      <div className="launchpad-admin-table-wrapper launchpad-admin-unimported-instances-table-wrapper overflow-x-auto">
        <Table className="launchpad-admin-table launchpad-admin-unimported-instances-table w-full grid-cols-[2fr_1.5fr_1.5fr_1fr_1.5fr_1fr]">
          <Table.Header className="launchpad-admin-table-header">
            <Table.Row className="launchpad-admin-table-header-row">
              <Table.Head
                className="launchpad-admin-table-header-cell launchpad-admin-column-name border-b border-neutral-300 bg-neutral-100 text-h6"
                data-column="name"
              >
                Name
              </Table.Head>
              <Table.Head
                className="launchpad-admin-table-header-cell launchpad-admin-column-display-name border-b border-neutral-300 bg-neutral-100 text-h6"
                data-column="display-name"
              >
                Display Name
              </Table.Head>
              <Table.Head
                className="launchpad-admin-table-header-cell launchpad-admin-column-template border-b border-neutral-300 bg-neutral-100 text-h6"
                data-column="template"
              >
                Template
              </Table.Head>
              <Table.Head
                className="launchpad-admin-table-header-cell launchpad-admin-column-state border-b border-neutral-300 bg-neutral-100 text-h6"
                data-column="state"
              >
                State
              </Table.Head>
              <Table.Head
                className="launchpad-admin-table-header-cell launchpad-admin-column-created-at border-b border-neutral-300 bg-neutral-100 text-h6"
                data-column="created-at"
              >
                Created At
              </Table.Head>
              <Table.Head
                className="launchpad-admin-table-header-cell launchpad-admin-column-actions border-b border-neutral-300 bg-neutral-100 text-h6"
                data-column="actions"
              >
                Action
              </Table.Head>
            </Table.Row>
          </Table.Header>
          <Table.Body className="launchpad-admin-table-body launchpad-admin-unimported-instances-table-body">
            {instances.map((instance, index) => {
              const isEven = index % 2 === 0;
              const cellBg = isEven ? 'bg-white' : 'bg-neutral-50';

              return (
                <Table.Row
                  key={instance.id}
                  className="launchpad-admin-table-row launchpad-admin-unimported-instance-row contents"
                  data-record-id={instance.id}
                  data-record-name={instance.name}
                  data-record-type="unimported-instance"
                  data-row-variant={isEven ? 'primary' : 'alternate'}
                >
                  <Table.Cell
                    className={clsx(
                      'launchpad-admin-table-cell launchpad-admin-unimported-instance-cell launchpad-admin-unimported-instance-cell-name border-b border-neutral-200',
                      cellBg,
                    )}
                    data-column="name"
                  >
                    <div className="launchpad-admin-cell-content">
                      <div className="launchpad-admin-unimported-instance-name text-body font-medium">
                        {instance.name}
                      </div>
                      <div className="launchpad-admin-unimported-instance-id text-caption text-neutral-500">
                        ID: {instance.id}
                      </div>
                    </div>
                  </Table.Cell>
                  <Table.Cell
                    className={clsx(
                      'launchpad-admin-table-cell launchpad-admin-unimported-instance-cell launchpad-admin-unimported-instance-cell-display-name border-b border-neutral-200',
                      cellBg,
                    )}
                    data-column="display-name"
                  >
                    <div className="launchpad-admin-cell-content launchpad-admin-unimported-instance-display-name text-body">
                      {instance.displayName}
                    </div>
                  </Table.Cell>
                  <Table.Cell
                    className={clsx(
                      'launchpad-admin-table-cell launchpad-admin-unimported-instance-cell launchpad-admin-unimported-instance-cell-template border-b border-neutral-200',
                      cellBg,
                    )}
                    data-column="template"
                  >
                    <div className="launchpad-admin-cell-content">
                      <div className="launchpad-admin-unimported-instance-template-name text-body">
                        {instance.templateName}
                      </div>
                      <div className="launchpad-admin-unimported-instance-template-version text-caption text-neutral-500">
                        {instance.templateVersion}
                      </div>
                    </div>
                  </Table.Cell>
                  <Table.Cell
                    className={clsx(
                      'launchpad-admin-table-cell launchpad-admin-unimported-instance-cell launchpad-admin-unimported-instance-cell-state border-b border-neutral-200',
                      cellBg,
                    )}
                    data-column="state"
                  >
                    <div className="launchpad-admin-cell-content">
                      <span
                        className={clsx(
                          'launchpad-admin-instance-state rounded px-2 py-1 text-caption',
                          {
                            'bg-success text-white':
                              instance.state === 'running',
                            'bg-neutral-300 text-neutral-700':
                              instance.state === 'stopped',
                            'bg-warning text-white':
                              instance.state !== 'running' &&
                              instance.state !== 'stopped',
                          },
                        )}
                        data-state={instance.state}
                      >
                        {instance.state}
                      </span>
                    </div>
                  </Table.Cell>
                  <Table.Cell
                    className={clsx(
                      'launchpad-admin-table-cell launchpad-admin-unimported-instance-cell launchpad-admin-unimported-instance-cell-created-at border-b border-neutral-200',
                      cellBg,
                    )}
                    data-column="created-at"
                  >
                    <div className="launchpad-admin-cell-content launchpad-admin-unimported-instance-created-at text-body text-neutral-700">
                      {new Date(instance.createdAt).toLocaleString()}
                    </div>
                  </Table.Cell>
                  <Table.Cell
                    className={clsx(
                      'launchpad-admin-table-cell launchpad-admin-unimported-instance-cell launchpad-admin-unimported-instance-cell-actions border-b border-neutral-200',
                      cellBg,
                    )}
                    data-column="actions"
                  >
                    <div className="launchpad-admin-cell-content launchpad-admin-record-actions">
                      <Button
                        onClick={() => handleSelect(instance)}
                        className="launchpad-admin-record-action px-3 py-1 text-caption"
                        data-action="select-instance"
                        data-record-id={instance.id}
                      >
                        Select
                      </Button>
                    </div>
                  </Table.Cell>
                </Table.Row>
              );
            })}
          </Table.Body>
        </Table>
      </div>
    </div>
  );
};
