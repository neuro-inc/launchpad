'use client';

import { useMemo, useRef, useState } from 'react';
import {
  closestCenter,
  DndContext,
  DragEndEvent,
  KeyboardSensor,
  PointerSensor,
  TouchSensor,
  useSensor,
  useSensors,
} from '@dnd-kit/core';
import {
  arrayMove,
  rectSortingStrategy,
  SortableContext,
  sortableKeyboardCoordinates,
  useSortable,
} from '@dnd-kit/sortable';
import { CSS } from '@dnd-kit/utilities';
import {
  faArrowRotateLeft,
  faArrowUpArrowDown,
  faGripDotsVertical,
} from '@fortawesome/pro-regular-svg-icons';

import { Template } from '@typings';

import { Badge, Button, Icon, Modal, ModalRef } from '@components/Shared';

type SortableAppCardProps = {
  position: number;
  template: Template;
};

const SortableAppCard: React.FC<SortableAppCardProps> = ({
  position,
  template,
}) => {
  const {
    attributes,
    listeners,
    setNodeRef,
    transform,
    transition,
    isDragging,
  } = useSortable({ id: template.id });

  return (
    <article
      ref={setNodeRef}
      className="launchpad-admin-app-order-card relative flex min-h-44 flex-col rounded-xl border border-neural-02 bg-white p-4 shadow-sm transition-[border-color,box-shadow,opacity] hover:border-primary-light hover:shadow-md"
      data-app-id={template.id}
      data-position={position}
      data-state={isDragging ? 'dragging' : 'idle'}
      style={{
        transform: CSS.Transform.toString(transform),
        transition,
        opacity: isDragging ? 0.55 : 1,
        zIndex: isDragging ? 10 : undefined,
      }}
    >
      <div className="flex items-start gap-3">
        <div className="flex size-11 shrink-0 items-center justify-center overflow-hidden rounded-xl border border-neural-02 bg-neural-01">
          {template.logo ? (
            // eslint-disable-next-line @next/next/no-img-element
            <img
              src={template.logo}
              alt=""
              className="size-full object-cover"
            />
          ) : (
            <span className="text-caption font-600 text-neural-04">
              {position}
            </span>
          )}
        </div>

        <div className="min-w-0 flex-1">
          <div className="flex items-center gap-2">
            <span className="flex size-6 shrink-0 items-center justify-center rounded-full bg-primary-subtle text-caption font-700 text-primary-dark">
              {position}
            </span>
            <h3 className="truncate text-h7 text-rebecca">
              {template.verboseName || template.name}
            </h3>
          </div>
          <p className="mt-1 truncate text-caption text-neural-04">
            {template.name}
          </p>
        </div>

        <button
          type="button"
          className="launchpad-admin-app-order-handle flex size-10 shrink-0 cursor-grab touch-none items-center justify-center rounded-lg text-neural-04 transition-colors hover:bg-primary-subtle hover:text-primary focus-visible:ring-2 focus-visible:ring-primary active:cursor-grabbing"
          aria-label={`Move ${template.verboseName || template.name}`}
          title="Drag to change position"
          {...attributes}
          {...listeners}
        >
          <Icon icon={faGripDotsVertical} />
        </button>
      </div>

      <p className="mt-4 line-clamp-2 text-body-medium text-neural-05">
        {template.descriptionShort || 'No description provided.'}
      </p>

      <div className="mt-auto flex items-center gap-2 pt-4">
        {template.isShared && <Badge variant="green">Shared</Badge>}
        {template.tags.slice(0, 2).map((tag, index) => (
          <Badge key={`${template.id}-${tag}-${index}`} variant="primary">
            {tag}
          </Badge>
        ))}
        {template.tags.length > 2 && (
          <span className="text-caption text-neural-04">
            +{template.tags.length - 2}
          </span>
        )}
      </div>
    </article>
  );
};

type AppsOrderModalProps = {
  templates: Template[];
  onSave: (templateIds: string[]) => Promise<void>;
};

export const AppsOrderModal: React.FC<AppsOrderModalProps> = ({
  templates,
  onSave,
}) => {
  const modalRef = useRef<ModalRef>(null);
  const visibleTemplates = useMemo(
    () => templates.filter((template) => !template.isInternal),
    [templates],
  );
  const [orderedTemplates, setOrderedTemplates] = useState(visibleTemplates);
  const [initialTemplateIds, setInitialTemplateIds] = useState(
    visibleTemplates.map(({ id }) => id),
  );
  const [isSaving, setIsSaving] = useState(false);

  const sensors = useSensors(
    useSensor(PointerSensor, {
      activationConstraint: { distance: 6 },
    }),
    useSensor(TouchSensor, {
      activationConstraint: { delay: 150, tolerance: 5 },
    }),
    useSensor(KeyboardSensor, {
      coordinateGetter: sortableKeyboardCoordinates,
    }),
  );

  const orderedTemplateIds = orderedTemplates.map(({ id }) => id);
  const hasChanges =
    orderedTemplateIds.length === initialTemplateIds.length &&
    orderedTemplateIds.some((id, index) => id !== initialTemplateIds[index]);

  const handleOpen = () => {
    setIsSaving(false);
    setOrderedTemplates(visibleTemplates);
    setInitialTemplateIds(visibleTemplates.map(({ id }) => id));
  };

  const handleDragEnd = ({ active, over }: DragEndEvent) => {
    if (!over || active.id === over.id) {
      return;
    }

    setOrderedTemplates((currentTemplates) => {
      const oldIndex = currentTemplates.findIndex(({ id }) => id === active.id);
      const newIndex = currentTemplates.findIndex(({ id }) => id === over.id);

      if (oldIndex === -1 || newIndex === -1) {
        return currentTemplates;
      }

      return arrayMove(currentTemplates, oldIndex, newIndex);
    });
  };

  const handleReset = () => {
    const templatesById = new Map(
      visibleTemplates.map((template) => [template.id, template]),
    );

    setOrderedTemplates(
      initialTemplateIds
        .map((id) => templatesById.get(id))
        .filter((template): template is Template => Boolean(template)),
    );
  };

  const handleSave = async () => {
    try {
      setIsSaving(true);
      await onSave(orderedTemplateIds);
      setInitialTemplateIds(orderedTemplateIds);
      modalRef.current?.close();
    } catch {
      // The parent reports the API error and the modal stays open for retrying.
    } finally {
      setIsSaving(false);
    }
  };

  return (
    <Modal
      ref={modalRef}
      disabled={visibleTemplates.length < 2}
      onOpen={handleOpen}
      content={
        <Modal.Content
          className="launchpad-admin-app-order-modal max-h-[90vh] w-[92vw] max-w-6xl"
          title="Arrange Launchpad apps"
          subtitle="Drag apps into the order users should see on the Launchpad."
        >
          <div className="py-2">
            <div className="mb-5 flex items-start gap-3 rounded-xl bg-primary-subtle/60 px-4 py-3 text-body-medium text-primary-dark">
              <Icon icon={faArrowUpArrowDown} className="mt-0.5 text-primary" />
              <p>
                The first app appears in the top-left position. Internal
                templates are excluded because they are not visible on the
                Launchpad.
              </p>
            </div>

            <DndContext
              sensors={sensors}
              collisionDetection={closestCenter}
              onDragEnd={handleDragEnd}
            >
              <SortableContext
                items={orderedTemplateIds}
                strategy={rectSortingStrategy}
              >
                <div
                  className="launchpad-admin-app-order-grid grid grid-cols-3 gap-4 sm:grid-cols-1 md:grid-cols-2"
                  data-section="app-order-grid"
                >
                  {orderedTemplates.map((template, index) => (
                    <SortableAppCard
                      key={template.id}
                      template={template}
                      position={index + 1}
                    />
                  ))}
                </div>
              </SortableContext>
            </DndContext>
          </div>

          <Modal.Footer
            className="launchpad-admin-app-order-footer justify-between"
            sticky
          >
            <Button
              variant="ghost"
              icon={faArrowRotateLeft}
              onClick={handleReset}
              disabled={!hasChanges || isSaving}
            >
              Reset
            </Button>
            <div className="flex gap-3">
              <Button
                variant="secondary"
                onClick={() => modalRef.current?.close()}
                disabled={isSaving}
              >
                Cancel
              </Button>
              <Button
                onClick={handleSave}
                disabled={!hasChanges}
                loading={isSaving}
              >
                Save order
              </Button>
            </div>
          </Modal.Footer>
        </Modal.Content>
      }
    >
      <Button
        className="launchpad-admin-arrange-apps-button h-10 shrink-0 px-4 sm:w-full"
        data-action="open-app-order"
        variant="primary-outline"
        icon={faArrowUpArrowDown}
        disabled={visibleTemplates.length < 2}
        title={
          visibleTemplates.length < 2
            ? 'At least two visible apps are required'
            : 'Arrange apps'
        }
      >
        Arrange apps
      </Button>
    </Modal>
  );
};
