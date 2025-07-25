export const conditionalProperty = <Property extends string, Value>(
  property: Property,
  value: Value | null | undefined,
): Partial<Record<Property, Value>> => {
  if (value != null) {
    return { [property]: value } as Record<Property, Value>;
  }

  return {};
};
