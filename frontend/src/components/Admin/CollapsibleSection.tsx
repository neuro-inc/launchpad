'use client';

import { useEffect, useState } from 'react';
import { faChevronDown } from '@fortawesome/pro-regular-svg-icons';
import clsx from 'clsx';

import { Button, Icon } from '@components/Shared';

type CollapsibleSectionProps = {
  title: string;
  children: React.ReactNode;
  defaultOpen?: boolean;
  isOpen?: boolean;
};

export const CollapsibleSection: React.FC<CollapsibleSectionProps> = ({
  title,
  children,
  defaultOpen = false,
  isOpen: controlledIsOpen,
}) => {
  const [isOpen, setIsOpen] = useState(defaultOpen);

  // Sync with controlled prop if provided
  useEffect(() => {
    if (controlledIsOpen !== undefined) {
      setIsOpen(controlledIsOpen);
    }
  }, [controlledIsOpen]);

  return (
    <div
      className="launchpad-admin-collapsible-section mb-6 rounded-lg border border-neutral-300"
      data-section="collapsible"
      data-state={isOpen ? 'open' : 'closed'}
      data-title={title}
    >
      <Button
        theme={false}
        onClick={() => setIsOpen(!isOpen)}
        className={clsx(
          'launchpad-admin-collapsible-trigger flex w-full items-center justify-between p-4',
          'text-left text-h5 font-medium',
          'transition-colors hover:bg-neutral-100',
          'focus:outline-none focus:ring-2 focus:ring-primary',
        )}
        data-action="toggle-section"
        aria-expanded={isOpen}
      >
        <span className="launchpad-admin-collapsible-title">{title}</span>
        <Icon
          icon={faChevronDown}
          className={clsx(
            'launchpad-admin-collapsible-icon transition-transform',
            isOpen && 'rotate-180',
          )}
        />
      </Button>
      {isOpen && (
        <div
          className="launchpad-admin-collapsible-content border-t border-neutral-300 p-4"
          data-section="collapsible-content"
        >
          {children}
        </div>
      )}
    </div>
  );
};
