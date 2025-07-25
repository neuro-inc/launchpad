import { isObject } from '@utils';

type Options = {
  skipNullable?: boolean;
};

export const isObjectEmpty = (value: any, options: Options = {}) => {
  const { skipNullable = false } = options;

  if (!isObject(value)) {
    throw Error('Value of isObjectEmpty utility is not an object');
  }

  if (skipNullable) {
    return !Object.values(value).filter(Boolean).length;
  }

  return !Object.keys(value).length;
};
