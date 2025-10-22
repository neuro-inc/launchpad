'use client';

import { faEye, faPencil, faTrash } from '@fortawesome/pro-regular-svg-icons';
import clsx from 'clsx';

import { Template } from '@typings';

import { Button, Icon, Table } from '@components/Shared';

type TemplatesTableProps = {
  templates: Template[];
  onView?: (template: Template) => void;
  onEdit?: (template: Template) => void;
  onDelete?: (template: Template) => void;
};

export const TemplatesTable: React.FC<TemplatesTableProps> = ({
  templates,
  onView,
  onEdit,
  onDelete,
}) => {
  if (templates.length === 0) {
    return (
      <div className="py-8 text-center text-neutral-500">
        No templates found. Import templates to get started.
      </div>
    );
  }

  return (
    <div className="overflow-x-auto">
      <Table className="w-full grid-cols-[auto_1.5fr_1fr_2fr_1fr_0.8fr_1.5fr]">
        <Table.Header>
          <Table.Row>
            <Table.Head className="border-b border-neutral-300 bg-neutral-100 text-h6">
              Logo
            </Table.Head>
            <Table.Head className="border-b border-neutral-300 bg-neutral-100 text-h6">
              Name
            </Table.Head>
            <Table.Head className="border-b border-neutral-300 bg-neutral-100 text-h6">
              Template
            </Table.Head>
            <Table.Head className="border-b border-neutral-300 bg-neutral-100 text-h6">
              Description
            </Table.Head>
            <Table.Head className="border-b border-neutral-300 bg-neutral-100 text-h6">
              Tags
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
          {templates.map((template, index) => {
            const isEven = index % 2 === 0;
            const cellBg = isEven ? 'bg-white' : 'bg-neutral-50';

            return (
              <Table.Row key={template.id}>
                <Table.Cell
                  className={clsx('border-b border-neutral-200', cellBg)}
                >
                  {template.logo ? (
                    <img
                      src={template.logo}
                      alt={template.verboseName}
                      width={40}
                      height={40}
                      className="rounded object-cover"
                    />
                  ) : (
                    <div className="flex size-10 items-center justify-center rounded bg-neutral-200">
                      <span className="text-caption text-neutral-500">N/A</span>
                    </div>
                  )}
                </Table.Cell>
                <Table.Cell
                  className={clsx('border-b border-neutral-200', cellBg)}
                >
                  <div className="text-body font-medium">
                    {template.verboseName}
                  </div>
                  <div className="text-caption text-neutral-500">
                    {template.name}
                  </div>
                </Table.Cell>
                <Table.Cell
                  className={clsx('border-b border-neutral-200', cellBg)}
                >
                  <div className="text-body">{template.templateName}</div>
                  <div className="text-caption text-neutral-500">
                    {template.templateVersion}
                  </div>
                </Table.Cell>
                <Table.Cell
                  className={clsx('border-b border-neutral-200', cellBg)}
                >
                  <div className="text-body text-neutral-700">
                    {template.descriptionShort || '-'}
                  </div>
                </Table.Cell>
                <Table.Cell
                  className={clsx('border-b border-neutral-200', cellBg)}
                >
                  <div className="flex flex-wrap gap-1">
                    {template.tags.length > 0 ? (
                      template.tags.map((tag, tagIndex) => (
                        <span
                          // eslint-disable-next-line react/no-array-index-key -- Index needed to handle duplicate tag values
                          key={`${template.id}-${tag}-${tagIndex}`}
                          className="rounded bg-primary-light px-2 py-1 text-caption text-primary-dark"
                        >
                          {tag}
                        </span>
                      ))
                    ) : (
                      <span className="text-caption text-neutral-500">-</span>
                    )}
                  </div>
                </Table.Cell>
                <Table.Cell
                  className={clsx('border-b border-neutral-200', cellBg)}
                >
                  <div className="flex flex-col gap-1">
                    {template.isInternal && (
                      <span className="rounded bg-neutral-200 px-2 py-1 text-caption text-neutral-700">
                        Internal
                      </span>
                    )}
                    {template.isShared && (
                      <span className="rounded bg-success px-2 py-1 text-caption text-white">
                        Shared
                      </span>
                    )}
                  </div>
                </Table.Cell>
                <Table.Cell
                  className={clsx('border-b border-neutral-200', cellBg)}
                >
                  <div className="flex flex-wrap gap-1">
                    <Button
                      variant="ghost"
                      onClick={() => onView?.(template)}
                      className="px-2 py-1 text-caption"
                      title="View template"
                    >
                      <Icon icon={faEye} className="mr-1" />
                      View
                    </Button>
                    <Button
                      variant="ghost"
                      onClick={() => onEdit?.(template)}
                      className="px-2 py-1 text-caption"
                      title="Edit template"
                    >
                      <Icon icon={faPencil} className="mr-1" />
                      Edit
                    </Button>
                    <Button
                      variant="ghost"
                      onClick={() => onDelete?.(template)}
                      className="px-2 py-1 text-caption text-error hover:bg-error-subtle"
                      title="Delete template"
                    >
                      <Icon icon={faTrash} className="mr-1" />
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
