import { toast as toastify, TypeOptions } from 'react-toastify';

import { AnyFunction } from '@typings';
import { isString } from '@utils';

import { Toast } from '@components/Ui/Toast';

type ToastType = Exclude<TypeOptions, 'default'>;

type CreateToasts<F extends AnyFunction> = { [key in ToastType]: F };

const TOAST_TYPE = {
  SUCCESS: 'success' as ToastType,
  WARNING: 'warning' as ToastType,
  ERROR: 'error' as ToastType,
  INFO: 'info' as ToastType,
} as const;

const createToasts = (fn: (type: ToastType) => void) =>
  Object.fromEntries(Object.values(TOAST_TYPE).map((type) => [type, fn(type)]));

/**
 * todo: resolve `createToasts` generated result
 */
// @ts-ignore
const toasting: CreateToasts<(message: string) => void> = createToasts(
  (type) => (message: string) => {
    toastify[type](<Toast>{message}</Toast>);
  },
);

type Options = {
  showEmptyMessage?: boolean;
};
/**
 * todo: resolve `createToasts` generated result
 */
// @ts-ignore
export const toast: CreateToasts<
  (message: string | null | undefined, options?: Options) => void
> = createToasts((type) => (message: string, options: Options = {}) => {
  const { showEmptyMessage = false } = options;

  if (!showEmptyMessage && !message) {
    return;
  }

  if (isString(message)) {
    toasting[type](message);
  }
});
