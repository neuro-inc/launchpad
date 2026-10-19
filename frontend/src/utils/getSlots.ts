import { Children, isValidElement } from 'react';

type Slots<T extends string> = {
  [K in T]?: React.ReactElement;
} & {
  content?: React.ReactNode;
};

/**
 * Extracts children nodes with `slot` attribute for Slot
 */
export const getSlots = <T extends string>(children: React.ReactNode) => {
  const collection = Children.toArray(children);

  const slots: Slots<T> = collection.reduce((components, component) => {
    // @ts-expect-error todo: fix type
    const { slot } = (component as React.ReactElement).props ?? {};

    if (slot) {
      return { ...components, [slot]: component };
    }

    return components;
  }, {});

  slots.content = collection.filter(
    // @ts-expect-error todo: fix type
    (component) => !(component as React.ReactElement).props?.slot,
  );

  return slots;
};

type ComponentMap = { [key: string]: React.FunctionComponent<any> };

export const getCompoundSlots = <T extends ComponentMap>(
  children: React.ReactNode,
  componentMap: T,
): {
  content: React.ReactNode[];
} & {
  [K in keyof T]?: React.ReactElement<any>;
} => {
  const childrenArray = Children.toArray(children);

  const slots = childrenArray.reduce(
    (accumulator, child) => {
      if (!isValidElement(child)) {
        accumulator.content.push(child);
        return accumulator;
      }

      const [alias] =
        Object.entries(componentMap).find(
          ([, component]) => component === child.type,
        ) ?? [];

      if (!alias) {
        accumulator.content.push(child);
        return accumulator;
      }

      accumulator[alias] = child as React.ReactElement<any>;
      return accumulator;
    },
    {
      content: [],
    } as {
      [key: string]: React.ReactElement<any> | React.ReactNode[];
      content: React.ReactNode[];
    },
  );

  return slots as {
    content: React.ReactNode[];
  } & {
    [K in keyof T]?: React.ReactElement<any>;
  };
};
