'use client';

import { faEye, faPencil, faTrash } from '@fortawesome/pro-regular-svg-icons';
import clsx from 'clsx';

import { Template } from '@typings';

import { Button, Icon, Table } from '@components/Shared';

const tableHeaders = [
  { key: 'logo', label: 'Logo' },
  { key: 'name', label: 'Name' },
  { key: 'template', label: 'Template' },
  { key: 'description', label: 'Description' },
  { key: 'tags', label: 'Tags' },
  { key: 'flags', label: 'Flags' },
  { key: 'actions', label: 'Actions' },
] as const;

type AdminSurfaceStyle = React.CSSProperties & {
  '--launchpad-admin-surface-background'?: string;
};

const getSurfaceStyle = (color: string): AdminSurfaceStyle => ({
  '--launchpad-admin-surface-background': color,
});

type TemplatesTableProps = {
  templates: Template[];
  onView?: (template: Template) => void;
  onEdit?: (template: Template) => void;
  onDelete?: (template: Template) => void;
  rowBgColor?: string;
  rowAltBgColor?: string;
  headerBgColor?: string;
};

export const TemplatesTable: React.FC<TemplatesTableProps> = ({
  templates,
  onView,
  onEdit,
  onDelete,
  rowBgColor,
  rowAltBgColor,
  headerBgColor,
}) => {
  const headerStyle = getSurfaceStyle(headerBgColor || '#f5f5f5');

  if (templates.length === 0) {
    return (
      <div
        className="launchpad-admin-empty-state launchpad-admin-templates-empty py-8 text-center text-neutral-500"
        data-section="templates-empty-state"
        data-state="empty"
      >
        No templates found. Import templates to get started.
      </div>
    );
  }

  return (
    <div
      className="launchpad-admin-table-wrapper launchpad-admin-templates-table-wrapper overflow-x-auto"
      data-section="templates-table"
    >
      <Table className="launchpad-admin-table launchpad-admin-templates-table w-full grid-cols-[auto_1.5fr_1fr_2fr_1fr_0.8fr_1.5fr]">
        <Table.Header className="launchpad-admin-table-header">
          <Table.Row className="launchpad-admin-table-header-row">
            {tableHeaders.map((header) => (
              <Table.Head
                key={header.key}
                className={clsx(
                  'launchpad-admin-table-header-cell launchpad-admin-templates-table-header-cell launchpad-admin-surface',
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

        <Table.Body className="launchpad-admin-table-body launchpad-admin-templates-table-body">
          {templates.map((template, index) => {
            const isEven = index % 2 === 0;
            const cellBg = isEven ? 'bg-white' : 'bg-neutral-50';
            const rowBackgroundColor = isEven
              ? rowBgColor || '#ffffff'
              : rowAltBgColor || '#fafafa';
            const rowStyle = getSurfaceStyle(rowBackgroundColor);

            return (
              <Table.Row
                key={template.id}
                className="launchpad-admin-table-row launchpad-admin-template-row contents"
                data-record-id={template.id}
                data-record-name={template.name}
                data-record-type="template"
                data-row-variant={isEven ? 'primary' : 'alternate'}
              >
                <Table.Cell
                  className={clsx(
                    'launchpad-admin-table-cell launchpad-admin-template-cell launchpad-admin-template-cell-logo launchpad-admin-surface border-b border-neutral-200',
                    cellBg,
                  )}
                  style={rowStyle}
                  data-column="logo"
                >
                  <div className="launchpad-admin-cell-content launchpad-admin-template-logo">
                    {template.logo ? (
                      // eslint-disable-next-line @next/next/no-img-element
                      <img
                        src={template.logo}
                        alt={template.verboseName}
                        width={40}
                        height={40}
                        className="launchpad-admin-template-logo-image rounded object-cover"
                      />
                    ) : (
                      <div className="launchpad-admin-template-logo-placeholder flex size-10 items-center justify-center rounded bg-neutral-200">
                        <span className="text-caption text-neutral-500">
                          N/A
                        </span>
                      </div>
                    )}
                  </div>
                </Table.Cell>
                <Table.Cell
                  className={clsx(
                    'launchpad-admin-table-cell launchpad-admin-template-cell launchpad-admin-template-cell-name launchpad-admin-surface border-b border-neutral-200',
                    cellBg,
                  )}
                  style={rowStyle}
                  data-column="name"
                >
                  <div className="launchpad-admin-cell-content">
                    <div className="launchpad-admin-template-display-name text-body font-medium">
                      {template.verboseName}
                    </div>
                    <div className="launchpad-admin-template-name text-caption text-neutral-500">
                      {template.name}
                    </div>
                  </div>
                </Table.Cell>
                <Table.Cell
                  className={clsx(
                    'launchpad-admin-table-cell launchpad-admin-template-cell launchpad-admin-template-cell-template launchpad-admin-surface border-b border-neutral-200',
                    cellBg,
                  )}
                  style={rowStyle}
                  data-column="template"
                >
                  <div className="launchpad-admin-cell-content">
                    <div className="launchpad-admin-template-source-name text-body">
                      {template.templateName}
                    </div>
                    <div className="launchpad-admin-template-version text-caption text-neutral-500">
                      {template.templateVersion}
                    </div>
                  </div>
                </Table.Cell>
                <Table.Cell
                  className={clsx(
                    'launchpad-admin-table-cell launchpad-admin-template-cell launchpad-admin-template-cell-description launchpad-admin-surface border-b border-neutral-200',
                    cellBg,
                  )}
                  style={rowStyle}
                  data-column="description"
                >
                  <div className="launchpad-admin-cell-content launchpad-admin-template-description text-body text-neutral-700">
                    {template.descriptionShort || '-'}
                  </div>
                </Table.Cell>
                <Table.Cell
                  className={clsx(
                    'launchpad-admin-table-cell launchpad-admin-template-cell launchpad-admin-template-cell-tags launchpad-admin-surface border-b border-neutral-200',
                    cellBg,
                  )}
                  style={rowStyle}
                  data-column="tags"
                >
                  <div className="launchpad-admin-cell-content launchpad-admin-template-tags flex flex-wrap gap-1">
                    {template.tags.length > 0 ? (
                      template.tags.map((tag, tagIndex) => (
                        <span
                          // eslint-disable-next-line react/no-array-index-key -- Index needed to handle duplicate tag values
                          key={`${template.id}-${tag}-${tagIndex}`}
                          className="launchpad-admin-template-tag rounded bg-primary-light px-2 py-1 text-caption text-primary-dark"
                          data-tag={tag}
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
                  className={clsx(
                    'launchpad-admin-table-cell launchpad-admin-template-cell launchpad-admin-template-cell-flags launchpad-admin-surface border-b border-neutral-200',
                    cellBg,
                  )}
                  style={rowStyle}
                  data-column="flags"
                >
                  <div className="launchpad-admin-cell-content launchpad-admin-template-flags flex flex-col gap-1">
                    {template.isInternal && (
                      <span
                        className="launchpad-admin-record-flag rounded bg-neutral-200 px-2 py-1 text-caption text-neutral-700"
                        data-flag="internal"
                      >
                        Internal
                      </span>
                    )}
                    {template.isShared && (
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
                    'launchpad-admin-table-cell launchpad-admin-template-cell launchpad-admin-template-cell-actions launchpad-admin-surface border-b border-neutral-200',
                    cellBg,
                  )}
                  style={rowStyle}
                  data-column="actions"
                >
                  <div className="launchpad-admin-cell-content launchpad-admin-record-actions flex flex-wrap gap-4">
                    <Button
                      variant="ghost"
                      onClick={() => onView?.(template)}
                      className="launchpad-admin-record-action h-auto gap-1 px-0 py-1 text-caption"
                      data-action="view-template"
                      data-record-id={template.id}
                      title="View template"
                    >
                      <Icon size="lg" icon={faEye} />
                      View
                    </Button>
                    <Button
                      variant="ghost"
                      onClick={() => onEdit?.(template)}
                      className="launchpad-admin-record-action h-auto gap-1 px-0 py-1 text-caption"
                      data-action="edit-template"
                      data-record-id={template.id}
                      title="Edit template"
                    >
                      <Icon size="lg" icon={faPencil} />
                      Edit
                    </Button>
                    <Button
                      variant="ghost"
                      onClick={() => onDelete?.(template)}
                      className="launchpad-admin-record-action h-auto gap-1 px-0 py-1 text-caption text-error hover:bg-error-subtle"
                      data-action="delete-template"
                      data-record-id={template.id}
                      title="Delete template"
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
