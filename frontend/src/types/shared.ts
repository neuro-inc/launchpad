import { Tagged } from 'type-fest';

export type AnyObject = { [key: string]: string };

export type AnyFunction = (...args: any[]) => any;

export type AsyncFunction = (...args: any[]) => Promise<any>;

export type Primitive = number | string | null | undefined;

/**
 * Used for dayjs
 */
export type DateFormat = Tagged<string, 'DateFormat'>;
export type IsoDate = Tagged<string, 'IsoDate'>;
export type UtcIsoDate = Tagged<string, 'UtcIsoDate'>;

export type Url = Tagged<string, 'URL'>;

/**
 * Shared
 */

export type ImageURL = Tagged<string, 'ImageURL'>;

export type FieldProps = {
  required?: boolean;
  className?: string;
  containerClassName?: string;
  variant?: 'floating' | 'static';
  label?: string;
  showError?: boolean;
  error?: string;
  note?: string;
  children?: React.ReactNode;
};

export type ModalProps = {
  closeModal?: () => void;
};

export type WithPagination<Item> = {
  page: number;
  pages: number;
  items: Item[];
};
