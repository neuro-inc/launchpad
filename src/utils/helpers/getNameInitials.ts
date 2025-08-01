export const getNameInitials = (value: string) =>
  value
    .replace(/[^a-zA-Z-\s]+/g, '')
    .split(' ')
    .map((partial) => partial[0])
    .filter(Boolean)
    .slice(0, 2)
    .join('');
