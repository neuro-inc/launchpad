/**
 * Extended from `react-router`
 */
type Invariant = {
  (value: boolean, message?: string): asserts value;
  <Value>(
    value: Value | null | undefined,
    message?: string,
  ): asserts value is Value;
};

/**
 * Narrows a value to more a specific type
 */
export const invariant: Invariant = (value: unknown, message?: string) => {
  if (value === false || value === null || typeof value === 'undefined') {
    throw new Error(message);
  }
};

export const warning = (condition: unknown, message: string) => {
  if (!condition) {
    if (typeof console !== 'undefined') {
      // eslint-disable-next-line no-console
      console.warn(message);
    }

    try {
      /**
       * This error is thrown as a convenience, so you can more easily
       * find the source for a warning that appears in the console by
       * enabling "pause on exceptions" in your JavaScript debugger.
       */
      throw new Error(message);
    } catch (error) {
      /**
       * Continue regardless error
       */
    }
  }
};
