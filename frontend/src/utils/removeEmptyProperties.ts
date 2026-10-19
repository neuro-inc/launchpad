type Options = {
  pattern?: any;
};

/**
 * Drops object nullable properties
 *
 * @example removeEmptyProperties({ foo: "foo", bar: null, baz: undefined, quax: "" });
 * // return { foo: "foo", quax: "" }
 *
 * @example removeEmptyProperties({ foo: "foo", quax: "" }, { pattern: "" });
 * // return { foo: "foo" }
 */
export const removeEmptyProperties = <Target extends Record<string, any>>(
  object: Target,
  options: Options = {},
): { [K in keyof Target]: Exclude<Target[K], null> } => {
  const { pattern } = options;

  return Object.fromEntries(
    Object.entries(object).filter(
      ([, value]) => value != null && value !== pattern,
    ),
  ) as { [K in keyof Target]: Exclude<Target[K], null> };
};
