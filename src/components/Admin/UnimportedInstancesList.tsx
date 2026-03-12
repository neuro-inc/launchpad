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
      <div className="py-8 text-center text-neutral-500">
        Loading running apps...
      </div>
    );
  }

  if (instances.length === 0) {
    return (
      <div className="py-8 text-center text-neutral-500">
        No running apps found to import.
      </div>
    );
  }

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <p className="text-body text-neutral-700">
          Found {instances.length} running app
          {instances.length !== 1 ? 's' : ''}
        </p>
        <Button
          type="button"
          onClick={fetchUnimportedInstances}
          theme={false}
          variant="ghost-primary"
          className="text-body"
        >
          Refresh
        </Button>
      </div>

      <div className="overflow-x-auto">
        <Table className="w-full grid-cols-[2fr_1.5fr_1.5fr_1fr_1.5fr_1fr]">
          <Table.Header>
            <Table.Row>
              <Table.Head className="border-b border-neutral-300 bg-neutral-100 text-h6">
                Name
              </Table.Head>
              <Table.Head className="border-b border-neutral-300 bg-neutral-100 text-h6">
                Display Name
              </Table.Head>
              <Table.Head className="border-b border-neutral-300 bg-neutral-100 text-h6">
                Template
              </Table.Head>
              <Table.Head className="border-b border-neutral-300 bg-neutral-100 text-h6">
                State
              </Table.Head>
              <Table.Head className="border-b border-neutral-300 bg-neutral-100 text-h6">
                Created At
              </Table.Head>
              <Table.Head className="border-b border-neutral-300 bg-neutral-100 text-h6">
                Action
              </Table.Head>
            </Table.Row>
          </Table.Header>
          <Table.Body>
            {instances.map((instance, index) => {
              const isEven = index % 2 === 0;
              const cellBg = isEven ? 'bg-white' : 'bg-neutral-50';

              return (
                <Table.Row key={instance.id}>
                  <Table.Cell
                    className={clsx('border-b border-neutral-200', cellBg)}
                  >
                    <div className="text-body font-medium">{instance.name}</div>
                    <div className="text-caption text-neutral-500">
                      ID: {instance.id}
                    </div>
                  </Table.Cell>
                  <Table.Cell
                    className={clsx('border-b border-neutral-200', cellBg)}
                  >
                    <div className="text-body">{instance.displayName}</div>
                  </Table.Cell>
                  <Table.Cell
                    className={clsx('border-b border-neutral-200', cellBg)}
                  >
                    <div className="text-body">{instance.templateName}</div>
                    <div className="text-caption text-neutral-500">
                      {instance.templateVersion}
                    </div>
                  </Table.Cell>
                  <Table.Cell
                    className={clsx('border-b border-neutral-200', cellBg)}
                  >
                    <span
                      className={clsx('rounded px-2 py-1 text-caption', {
                        'bg-success text-white': instance.state === 'running',
                        'bg-neutral-300 text-neutral-700':
                          instance.state === 'stopped',
                        'bg-warning text-white':
                          instance.state !== 'running' &&
                          instance.state !== 'stopped',
                      })}
                    >
                      {instance.state}
                    </span>
                  </Table.Cell>
                  <Table.Cell
                    className={clsx('border-b border-neutral-200', cellBg)}
                  >
                    <div className="text-body text-neutral-700">
                      {new Date(instance.createdAt).toLocaleString()}
                    </div>
                  </Table.Cell>
                  <Table.Cell
                    className={clsx('border-b border-neutral-200', cellBg)}
                  >
                    <Button
                      onClick={() => handleSelect(instance)}
                      className="px-3 py-1 text-caption"
                    >
                      Select
                    </Button>
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
