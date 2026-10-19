import { isArray, isNumber } from '@utils';

type Props = {
  if?: any;
  children?: React.ReactNode;
};

/**
 * Conditional render to improve readability
 */
export const Render = ({ if: source = false, children }: Props) => {
  if (source === null) {
    return source;
  }

  if (isArray(source)) {
    return source.filter(Boolean).length ? children : null;
  }

  if (isNumber(source)) {
    return children;
  }

  if (source) {
    return children;
  }

  return null;
};
