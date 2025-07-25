import { isArray } from '@utils';

export const formatToCamelCase = (
  item: any,
  level: number = Infinity,
): unknown => {
  if (isArray(item)) {
    return item.map((item) => formatToCamelCase(item, level));
  }

  if (typeof item === 'function' || item !== Object(item)) {
    return item;
  }

  if (level <= 0) {
    return item;
  }

  return Object.fromEntries(
    Object.entries(item).map(([key, value]) => [
      key.replace(/([-_][a-z])/gi, (c) => c.toUpperCase().replace(/[-_]/g, '')),
      formatToCamelCase(value, level - 1),
    ]),
  );
};
