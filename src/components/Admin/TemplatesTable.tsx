'use client';

import {
  faEye,
  faLayerGroup,
  faPencil,
  faTrash,
} from '@fortawesome/pro-regular-svg-icons';
import clsx from 'clsx';

import { Template } from '@typings';

import { Button, ChaseSpinner, Icon, Table } from '@components/Shared';

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
  isLoading?: boolean;
  onView?: (template: Template) => void;
  onEdit?: (template: Template) => void;
  onDelete?: (template: Template) => void;
  rowBgColor?: string;
  rowAltBgColor?: string;
  headerBgColor?: string;
};

export const TemplatesTable: React.FC<TemplatesTableProps> = ({
  templates,
  isLoading = false,
  onView,
  onEdit,
  onDelete,
  rowBgColor,
  rowAltBgColor,
  headerBgColor,
}) => {
  const headerStyle = getSurfaceStyle(headerBgColor || '#f5f5f5');

  if (!isLoading && templates.length === 0) {
    return (
      <div
        className="launchpad-admin-empty-state launchpad-admin-templates-empty flex min-h-28 flex-col items-center justify-center px-6 py-10 text-center"
        data-section="templates-empty-state"
        data-state="empty"
      >
        <div className="mb-4 flex size-14 items-center justify-center rounded-2xl bg-primary-subtle text-primary">
          <Icon icon={faLayerGroup} size="lg" />
        </div>
        <h3 className="text-h6 font-600 text-rebecca">No templates yet</h3>
        <p className="mt-1 max-w-md text-body-medium text-neural-04">
          Import a template to define an application that can be deployed
          through Launchpad.
        </p>
      </div>
    );
  }

  return (
    <div
      className="launchpad-admin-table-wrapper launchpad-admin-templates-table-wrapper min-h-28 overflow-x-auto"
      data-section="templates-table"
      data-state={isLoading ? 'loading' : 'loaded'}
    >
      <Table
        className="launchpad-admin-table launchpad-admin-templates-table min-w-[1180px] grid-cols-[72px_1.4fr_1fr_2fr_1fr_0.8fr_1.5fr] rounded-none bg-transparent"
        aria-busy={isLoading}
      >
        <Table.Header className="launchpad-admin-table-header">
          <Table.Row className="launchpad-admin-table-header-row">
            {tableHeaders.map((header) => (
              <Table.Head
                key={header.key}
                className={clsx(
                  'launchpad-admin-table-header-cell launchpad-admin-templates-table-header-cell launchpad-admin-surface',
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
                  className="launchpad-admin-table-row launchpad-admin-template-row group contents"
                  data-record-id={template.id}
                  data-record-name={template.name}
                  data-record-type="template"
                  data-row-variant={isEven ? 'primary' : 'alternate'}
                >
                  <Table.Cell
                    className={clsx(
                      'launchpad-admin-table-cell launchpad-admin-template-cell launchpad-admin-template-cell-logo launchpad-admin-surface border-b border-neural-02 transition-[filter] group-hover:brightness-[0.985]',
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
                          className="launchpad-admin-template-logo-image size-11 rounded-xl border border-neural-02 bg-white object-cover p-0.5"
                        />
                      ) : (
                        <div className="launchpad-admin-template-logo-placeholder flex size-11 items-center justify-center rounded-xl border border-neural-02 bg-neural-01">
                          <span className="text-caption text-neutral-500">
                            N/A
                          </span>
                        </div>
                      )}
                    </div>
                  </Table.Cell>
                  <Table.Cell
                    className={clsx(
                      'launchpad-admin-table-cell launchpad-admin-template-cell launchpad-admin-template-cell-name launchpad-admin-surface border-b border-neural-02 transition-[filter] group-hover:brightness-[0.985]',
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
                      'launchpad-admin-table-cell launchpad-admin-template-cell launchpad-admin-template-cell-template launchpad-admin-surface border-b border-neural-02 transition-[filter] group-hover:brightness-[0.985]',
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
                      'launchpad-admin-table-cell launchpad-admin-template-cell launchpad-admin-template-cell-description launchpad-admin-surface border-b border-neural-02 transition-[filter] group-hover:brightness-[0.985]',
                      cellBg,
                    )}
                    style={rowStyle}
                    data-column="description"
                  >
                    <div className="launchpad-admin-cell-content launchpad-admin-template-description text-body-medium leading-5 text-neural-05">
                      {template.descriptionShort || '-'}
                    </div>
                  </Table.Cell>
                  <Table.Cell
                    className={clsx(
                      'launchpad-admin-table-cell launchpad-admin-template-cell launchpad-admin-template-cell-tags launchpad-admin-surface border-b border-neural-02 transition-[filter] group-hover:brightness-[0.985]',
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
                            className="launchpad-admin-template-tag rounded-full bg-primary-subtle px-2.5 py-1 text-caption font-500 text-primary-dark"
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
                      'launchpad-admin-table-cell launchpad-admin-template-cell launchpad-admin-template-cell-flags launchpad-admin-surface border-b border-neural-02 transition-[filter] group-hover:brightness-[0.985]',
                      cellBg,
                    )}
                    style={rowStyle}
                    data-column="flags"
                  >
                    <div className="launchpad-admin-cell-content launchpad-admin-template-flags flex flex-col items-start gap-1">
                      {template.isInternal && (
                        <span
                          className="launchpad-admin-record-flag rounded-full bg-neural-01 px-2.5 py-1 text-caption font-500 text-neural-05"
                          data-flag="internal"
                        >
                          Internal
                        </span>
                      )}
                      {template.isShared && (
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
                      'launchpad-admin-table-cell launchpad-admin-template-cell launchpad-admin-template-cell-actions launchpad-admin-surface border-b border-neural-02 transition-[filter] group-hover:brightness-[0.985]',
                      cellBg,
                    )}
                    style={rowStyle}
                    data-column="actions"
                  >
                    <div className="launchpad-admin-cell-content launchpad-admin-record-actions flex flex-wrap gap-1">
                      <Button
                        variant="ghost"
                        onClick={() => onView?.(template)}
                        className="launchpad-admin-record-action h-9 gap-1.5 rounded-lg px-2.5 py-1 text-body-small font-600 hover:bg-primary-subtle"
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
                        className="launchpad-admin-record-action h-9 gap-1.5 rounded-lg px-2.5 py-1 text-body-small font-600 hover:bg-primary-subtle"
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
                        className="launchpad-admin-record-action h-9 gap-1.5 rounded-lg px-2.5 py-1 text-body-small font-600 text-error hover:bg-error-subtle"
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
        )}
      </Table>
      {isLoading && (
        <div
          className="launchpad-admin-table-loading flex min-h-28 items-center justify-center gap-3 bg-white text-neural-04"
          data-section="templates-loading-state"
          data-state="loading"
        >
          <ChaseSpinner
            color="primary"
            className="launchpad-admin-loading-spinner size-5"
          />
          <span className="text-body-medium">Loading templates...</span>
        </div>
      )}
    </div>
  );
};
