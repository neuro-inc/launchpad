import { SnakeCasedPropertiesDeep } from 'type-fest';

export const formatToSnakeCase = <
  Input,
  SnakeCased extends SnakeCasedPropertiesDeep<Input>,
>(
  input: Input,
): Input | SnakeCased | SnakeCased[] => {
  if (typeof input === 'object' && input !== null) {
    const formattedObject = {} as SnakeCased;

    if (Array.isArray(input)) {
      return input.map(formatToSnakeCase);
    }

    Object.keys(input).forEach((key) => {
      const snakeCaseKey = key
        .replace(/([a-z])([A-Z0-9])/g, '$1_$2')
        .toLowerCase();
      // @ts-expect-error todo: resolve error
      formattedObject[snakeCaseKey] = formatToSnakeCase(input[key]);
    });

    return formattedObject;
  }

  return input;
};
